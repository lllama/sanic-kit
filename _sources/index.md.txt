# SanicKit

:::{image} logo.png
:width: 250px
:::

<hr>

SanicKit adds file-path routing to [Sanic](https://sanic.dev/), inspired by [Svelte Kit](http://kit.svelte.dev). The handler and template code are both included in the same `.sanic` file, to help promote [Locality of
Behvaiour](https://htmx.org/essays/locality-of-behaviour/). 

Support for [HTMX](http://htmx.org) is built in. In particular, middleware is
included to help handle HTMX requests and responses. Support for [template fragments](https://htmx.org/essays/template-fragments/) is also included (thanks to [Jinja2 Fragments](https://github.com/sponsfreixes/jinja2-fragments)). 

## Installation

To install SanicKit, create a new virtual environment and install `sanickit` with:

```bash
python -m venv .venv
. ./.venv/bin/activate
python -m pip install sanickit
```

This will install the `sk` command line tool. Create a new skeleton project with:

```bash
sk new
```

This will create the following source tree:

```
.
├── README.md
├── src
│   ├── +head.html
│   ├── blueprints
│   ├── index.html
│   ├── lib
│   ├── middleware
│   │   └── htmx.py
│   ├── routes
│   │   ├── +layout.html
│   │   ├── +page.sanic
│   └── server_setup.py
└── static
    └── app.css
```

The files and folders serve the following purposes:

- `+head.html` - Information contained in the `<head>` of pages returned by the server.
- `blueprints` - Any python files created here will be added as
   [blueprints](https://sanic.dev/en/guide/best-practices/blueprints.html) to the app.
- `index.html` - the base template for all pages.
- `lib` - any code included here can be imported into handlers by importing from `.lib`. E.g. `from .lib.auth import my_auth_helper`
- `middleware` - any code included here will be imported as middleware by the app.
- `routes` - All file paths in this folder will be recreated as URLs in the app. See [routes](routes.md) for more info. 
   - `+page.sanic` - These files contain the handler code for `GET` requests and the page template.
   - `+layout.html` - a template that any routes in this folder or below will inherit from this template.
- `server_setup.py` - Code for [server life-cycle events.](https://sanic.dev/en/guide/basics/listeners.html#attaching-a-listener)
- `static` - Files that will be served from the `/static/` route.
   - `static/app.css` - Default CSS file.


:::{toctree} Table of Contents
:hidden:
:depth: 3
routes
handlers
templates
:::

