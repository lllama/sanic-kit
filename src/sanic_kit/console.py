import os
import subprocess
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from pathlib import Path

import tomlkit
from rich import print
from textual.app import App
from textual.binding import Binding
from textual.containers import Grid, Horizontal
from textual.message import Message
from textual.screen import ModalScreen
from textual.widget import Widget
from textual.widgets import (Button, Checkbox, DirectoryTree, Footer, Header,
                             Input, Label, TabbedContent, TextLog)


class NewRoute(ModalScreen):
    class CreateRoute(Message):
        def __init__(self, route):
            super().__init__()
            self.route = route

    def on_mount(self):
        self.query_one(Input).focus()

    def compose(self):
        with Grid(id="newroute"):
            yield Label("Add new route")
            yield Input(placeholder="new route")

    def on_input_submitted(self, event):
        self.app.post_message(self.CreateRoute(event.input.value))
        self.app.pop_screen()


class Logo(Label):
    def render(self):
        return (
            "[white on #ea386b]"
            "                     \n"
            "   ▄███ █████ ██     \n"
            "   ██                \n"
            "    ▀███████ ███▄    \n"
            "                ██   \n"
            "   ████ ████████▀    \n"
            "                     \n"
        )


class Config(Widget):
    class AddUnpkg(Message):
        def __init__(self, package):
            super().__init__()
            self.package = package

    class RemoveUnpkg(Message):
        def __init__(self, package):
            super().__init__()
            self.package = package

    class AddStylesheet(Message):
        def __init__(self, stylesheet):
            super().__init__()
            self.stylesheet = stylesheet

    class RemoveStylesheet(Message):
        def __init__(self, stylesheet):
            super().__init__()
            self.stylesheet = stylesheet

    class ToggleTailwind(Message):
        def __init__(self, value):
            super().__init__()
            self.value = value

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.unpkg_config = config["sanic-kit"].get("unpkgs", [])
        self.stylesheets_config = config["sanic-kit"].get("stylesheets", [])

    STYLESHEETS = {
        "classless": "https://classless.de/classless.css",
        "Pico": "https://www.jsdelivr.com/package/npm/@picocss/pico",
    }

    UNPKG = {
        "HTMX": "htmx.org",
        "Hyperscript": "hyperscript.org",
        "AlpineJs": "alpinejs",
        "Petite-Vue": "petite-vue",
    }

    def compose(self):
        yield Label("JavaScript Libraries")
        for pkg, value in self.UNPKG.items():
            yield Checkbox(pkg, value=value in self.unpkg_config)

        yield Label("CSS Libraries")
        for css, value in self.STYLESHEETS.items():
            yield Checkbox(css, value=value in self.stylesheets_config)

        yield Checkbox("Tailwind", value=self.config["sanic-kit"].get("tailwind"))

    def on_checkbox_changed(self, event: Checkbox.Changed):
        label = str(event.checkbox.label)
        if label in self.UNPKG:
            if event.checkbox.value:
                self.post_message(self.AddUnpkg(self.UNPKG[label]))
            else:
                self.post_message(self.RemoveUnpkg(self.UNPKG[label]))
        if label in self.STYLESHEETS:
            if event.checkbox.value:
                self.post_message(self.AddStylesheet(self.STYLESHEETS[label]))
            else:
                self.post_message(self.RemoveStylesheet(self.STYLESHEETS[label]))
        if label == "Tailwind":
            self.post_message(self.ToggleTailwind(event.checkbox.value))


class Server(Widget):
    def compose(self):
        with Horizontal():
            yield Button("Start")
            yield Button("Restart", disabled=True)
        yield TextLog()


class Routes(Widget):
    def __init__(self, root):
        super().__init__()
        self.root = root

    def update_preview(self, node):
        textlog = self.query_one(TextLog)
        textlog.clear()
        textlog.write(Path(node.path).read_text())

    def on_tree_node_highlighted(self, event):
        if not event.node.data.is_dir:
            self.update_preview(event.node.data)

    def on_directory_tree_file_selected(self, event):
        self.update_preview(event)

    def compose(self):
        with Horizontal():
            yield Button("Add route", id="addroute")
            yield Button("Add layout")
        with Horizontal():
            yield DirectoryTree(self.root)
            yield TextLog(highlight=True, classes="hidden")

    async def refresh_tree(self, path_to_select):
        tree = self.query_one(DirectoryTree)
        await tree.remove()
        await self.mount(DirectoryTree(self.root))
        tree = self.query_one(DirectoryTree)

        path_parts = path_to_select.relative_to(self.root).parts

        node = tree.root
        current_path = Path(self.root)
        for part in path_parts:
            node = [n for n in node.children if Path(n.data.path) == current_path / part][0]
            if node.data.is_dir:
                tree.load_directory(node)
            else:
                tree.select_node(node)
            current_path = current_path / part

        tree.select_node(node)


class SanicKit(App):
    CSS_PATH = "console.css"

    BINDINGS = [
        Binding(key="q", action="quit", description="Quit the app"),
        Binding(key="a", action="add_route", description="Add route"),
        Binding(key="e", action="edit_route", description="Edit route"),
    ]

    @contextmanager
    def suspend(self):
        driver = self._driver
        if driver is not None:
            driver.stop_application_mode()

            with redirect_stdout(sys.__stdout__), redirect_stderr(sys.__stderr__):
                yield

            driver.start_application_mode()

    def action_add_route(self):
        self.push_screen(NewRoute())

    async def action_edit_route(self):
        tree = self.query_one(DirectoryTree)
        self.log(tree.cursor_node)
        if not (file := tree.cursor_node.data).is_dir:
            self.log(f"editing file {file.path}")
            with self.suspend():
                subprocess.run([os.environ["EDITOR"], file.path])

    async def on_load(self):
        if (pyproj := Path("pyproject.toml")).exists():
            self.config = tomlkit.parse(pyproj.read_text())
            if "sanic-kit" not in self.config:
                self.config["sanic-kit"] = tomlkit.table()
        else:
            print("[yellow]pyproject.toml[/yellow] [red]not found")
            await self.action_quit()

    def add_to_list(self, list_name, item):
        sk_table = self.config["sanic-kit"]
        if list_name not in sk_table:
            sk_table.add(list_name, [item])
        elif item not in sk_table[list_name]:
            sk_table[list_name].append(item)
        self.save_config()

    def remove_from_list(self, list_name, item):
        sk_table = self.config["sanic-kit"]
        if list_name in sk_table and item in sk_table[list_name]:
            sk_table[list_name].remove(item)
        self.save_config()

    def on_config_add_unpkg(self, message):
        package = message.package
        self.add_to_list("unpkgs", package)

    def on_config_remove_unpkg(self, message):
        package = message.package
        self.remove_from_list("unpkgs", package)

    def on_config_add_stylesheet(self, message):
        stylesheet = message.stylesheet
        self.add_to_list("stylesheets", stylesheet)

    def on_config_remove_stylesheet(self, message):
        stylesheet = message.stylesheet
        self.remove_from_list("stylesheets", stylesheet)

    def on_config_toggle_tailwind(self, message):
        self.config["sanic-kit"]["tailwind"] = message.value
        self.save_config()

    def save_config(self):
        Path("pyproject.toml").write_text(tomlkit.dumps(self.config))

    def on_button_pressed(self, event):
        match event.button.id:
            case "addroute":
                self.push_screen(NewRoute())

    async def on_new_route_create_route(self, message):
        new_dir = Path("src/routes") / message.route
        new_dir.mkdir(exist_ok=True, parents=True)
        new_page = new_dir / "+page.sanic"
        new_page.touch()
        await self.query_one(Routes).refresh_tree(new_page)

    def compose(self):
        yield Header()
        with Horizontal():
            yield Logo()
            with TabbedContent("Routes", "Server", "Config"):
                yield Routes("./src/routes")
                yield Server()
                yield Config(self.config)
        yield Footer()