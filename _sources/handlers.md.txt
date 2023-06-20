# Handlers

`+page.sanic` files can contain a `<handler>` tag that contains the python code for `GET` requests. 

The code gets compiled into a standard Sanic handler that is passed the current `request` along with any path parameters. It also gets passed a `TEMPLATE` parameter that contains the template name for the route. 

## Path parameters

By default, all path parameters are passed as strings. Sanic supports converting the parameters into specific types (see the [Sanic docs](https://sanic.dev/en/guide/basics/routing.html#http-methods) for the supported types). To perform this conversion in SanicKit, specify the types as attributes in the `<handler>` tag. E.g. `<handler id=“int” article=“uuid”>` will convert the `id` parameter to an int and ensure the `article` parameter is a valid UUID.

## Imports

If you need to import any code then just use standard import statements. These will be extracted from the function and placed at the module level along with any imports from other handlers. 

### `Lib` and relative imports

Any code put in the `lib` folder can be imported using the relative `.lib` import. E.g. `from .lib.my_module import my_function`

Any Python files placed in the same directory as the `+page.sanic` file can also be imported using standard relative import syntax. E.g. `from .my_file import my_function`

##  Returning 

There is no need to specify a return statement for the handler function. The default behaviour is for the handler to pass the current local variables to the template as its context. (I.e. the context is set to `locals()`.)

If you need or want to return early, then you can use the `template()` helper function. Adding a `return template()` statement, will return the template and pass the value of `locals()` as its context. You can also return any other valid Sanic response wherever you want. 

If you want to return a template fragment then you can use the `fragment` helper function. Using `return fragment(<fragment name>)` will pass the value of `locals()` to the template and return the block with the same name as the requested fragment. 


##  Helper function reference

###  `template`

Returns the current template and passes the current value of `locals()` as its context. 

###  `fragment`

The first parameter is a block name that will be returned instead of the full template. The current value of `locals()` is passed as its context. 

