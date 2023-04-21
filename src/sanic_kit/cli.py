import os
import shutil
import subprocess
from contextlib import chdir
from dataclasses import dataclass
from importlib.util import find_spec
from multiprocessing import Process
from pathlib import Path
from textwrap import dedent

import click
from bs4 import BeautifulSoup as BS
from copier import run_auto
from jinja2 import BaseLoader, Environment
from rich import print
from rich.markup import escape
from tomlkit import loads
from watchfiles import watch

from .code import extract_api, extract_imports


@click.group()
def cli():
    ...


@cli.command
@click.argument("path", type=click.Path(file_okay=False, path_type=Path))
@click.pass_context
def new(ctx: click.Context, path: Path):
    if path.exists():
        print("[red]Path already exists")
        ctx.exit()

    print(f"[green]Creating app in [yellow]{path}")

    run_auto(str(Path(__file__).parent.parent.parent / "templates" / "default"), path)

    for route in path.glob("**/.gitkeep"):
        route.unlink()


jinja_env = Environment(loader=BaseLoader())

ENDPOINT_TEMPLATE = jinja_env.from_string(
    """
{% for import in imports %}
{{ import -}}
{% endfor %}

@bp.{{method|lower}}("{{route}}", name="{{name}}")
{{code}}
"""
)


def handle_server(src, route, template_name):
    parameters = [x[1:-1] for x in route.parts if x.startswith("[") and x.endswith("]")]
    route_url = (
        str(route.relative_to(src / "routes").parent)
        .replace(os.sep, "/")
        .replace(".", "/")
        .replace("[", "<")
        .replace("]", ">")
    )

    name = (
        str(route.relative_to(src / "routes").parent)
        .replace(os.sep, "_")
        .replace(".", "index")
        .replace("[", "")
        .replace("]", "")
    )
    imports, handlers = extract_api(route, name, template_name, parameters)
    # Create the code
    code = [
        ENDPOINT_TEMPLATE.render(
            imports=imports,
            route=route_url,
            name=handler.name,
            method=handler.method,
            template=template_name,
            code=handler.code,
        )
        for handler in handlers
    ]

    return '\n'.join(code)
def find_nearest_layout(route):
    while not (layout := route.parent / "+layout.html").exists():
        route = route.parent
        if route.stem == "src":
            break
    return layout


def handle_page(src, route, templates, template_name):
    html = BS(route.read_text(), "html.parser")

    layout = find_nearest_layout(route)
    layout_name = str(layout).replace(os.sep, "_").replace("[", "").replace("]", "")
    (templates / template_name).write_text(f"""{{% extends "{layout_name}" %}}\n\n""" + html.prettify())

    parameters = [x[1:-1] for x in route.parts if x.startswith("[") and x.endswith("]")]
    route_url = (
        str(route.relative_to(src / "routes").parent)
        .replace(os.sep, "/")
        .replace(".", "/")
        .replace("[", "<")
        .replace("]", ">")
    )

    name = (
        str(route.relative_to(src / "routes").parent)
        .replace(os.sep, "_")
        .replace(".", "index")
        .replace("[", "")
        .replace("]", "")
    )
    if script := html.find("handler"):
        python = dedent(script.extract().text)
        imports, python = extract_imports(python, name, template_name, parameters)
        # Create the code
    else:
        imports, python = extract_imports("", name, template_name, parameters)
    return ENDPOINT_TEMPLATE.render(
        imports=imports,
        route=route_url,
        name=name,
        method="get",
        template=template_name,
        code=python,
    )


def _build(restart=False):
    base = Path(".")
    src = base / "src"

    build_root = Path("build")

    if not restart:
        shutil.rmtree(build_root, ignore_errors=True)

    build = build_root / "app"
    build.mkdir(exist_ok=True, parents=True)

    (build / "__init__.py").touch()

    (build / "blueprints").mkdir(exist_ok=True)
    (build / "blueprints" / "__init__.py").touch()
    (build / "middleware").mkdir(exist_ok=True)
    (build / "lib").mkdir(exist_ok=True)
    (build / "static").mkdir(exist_ok=True)
    templates = build_root / "templates"
    templates.mkdir(exist_ok=True)

    # Make the server
    shutil.copy(find_spec("sanic_kit.template.server").origin, build / "server.py")

    app_blueprint = """
from sanic import Blueprint
from sanic_ext import render


bp = Blueprint("app")

"""

    for route in (src / "routes").glob("**/*"):
        print(f"[green]Processing: [yellow]{escape(str(route))}")
        # (build / route.parent).mkdir(parents=True, exist_ok=True)

        # shutil.copy(route, build / route)

        template_name = f"{str(route.with_suffix('')).replace(os.sep, '_')}.html"
        # Create our template
        match route.name:
            case "+page.sanic":
                app_blueprint += handle_page(src, route, templates, template_name)
            case "+server.py":
                app_blueprint += handle_server(src, route, template_name)
            case "+layout.html":
                html = BS(route.read_text(), "html.parser")
                (templates / template_name).write_text("""{% extends "index.html" %}\n\n""" + html.prettify())

    (build / "blueprints" / "app.py").write_text(app_blueprint)

    shutil.copy(src / "index.html", templates)

    shutil.copytree(base / "static", build / "static", dirs_exist_ok=True)
    shutil.copytree(build / "lib", build / "lib", dirs_exist_ok=True)


@cli.command
def build():
    _build()


def watch_files():
    try:
        for change in watch(Path("test")):
            _build(restart=True)
    except KeyboardInterrupt:
        pass


@cli.command
def run():
    _build()
    file_watcher = Process(target=watch_files)
    file_watcher.start()
    try:
        with chdir(Path("build")):
            proc = subprocess.run(["sanic", "app.server:create_app", "--debug", "--dev"], check=True)
    except KeyboardInterrupt:
        file_watcher.close()


if __name__ == "__main__":
    cli()
