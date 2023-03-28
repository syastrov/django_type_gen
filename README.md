# django_type_gen
Generate static type annotations for Django models in .py source files for Django projects, using libcst

Right now, it can add to your models:
- `id` annotation (it currently assumes it's an int)
- `pk` annotation
- `FK_id` annotation for foreign keys
- Annotations for `RelatedManager`s for the reverse accessors for foreign keys

This is a proof-of-concept and is by no means production ready. Use at your own risk.

The idea is that this will essentially add all the type annotations that you would ordinarily have to add manually
if you were using the Django type stubs from https://github.com/sbdchd/django-types.

This means that you will be able to get static type-checking support for Django's "magic", for type-checkers other than
mypy (or with mypy, but without using any mypy plugins).

Please note:
1. You must have the environment variable `DJANGO_SETTINGS_MODULE` set
2. Your code will be executed in order to gather data about your Django models from the model registry.
   If you have side effects from initializing Django and/or your 
   modules, then take caution or this project might not be for you.

Please first install libcst into your project's Python environment (note: it):

`pip3 install libcst==0.4.1`

> Note: This specific version of libcst does not have issues with the `FullyQualifiedNameProvider`.
> I believe the problem will be fixed in a future release. See https://github.com/Instagram/LibCST/pull/867

Clone this project into a subfolder of your project.

Create a `.libcst.codemod.yaml` file in your project's root.
It should at least contain the following:
```yaml
modules:
# List of modules that contain codemods inside of them.
- 'libcst.codemod.commands'
- 'django_type_gen.commands'
```

Run the codemod on your project, passing in the relevant files which might contain Django models (e.g. all `models.py` files or `*/models/*.py` files):

`python3 -m libcst.tool codemod django_type_gen.AddTypesToDjangoModels $(find . -name 'models.py' -o \( -wholename '*/models/*.py' \)) --no-format`

You will notice that type annotations have been added to your `.py` source files.
It is not the intention that you should commit these, as they clutter your source code and will be regenerated next 
time, but that is up to you.

Then you can, for example, run the `pyright` type-checker on your project.

Note: You will have to rerun the codemod any time you change your models to regenerate the type annotations.


# Limitations

There are (probably) many. See also TODOs in the code.

# Future thoughts

It would be ideal if the generated type annotations could live outside of your source files
(so you would not have to commit them to version control, and so they would not clutter your code).

Ideally, there would be a way of specifying "overlay" stub files, which would augment the code in some way.
Something like this has been discussed on the typing-sig mailing list:
https://mail.python.org/archives/list/typing-sig@python.org/thread/UOIVXOJA2PIEYF3XB37HBI2MAJ4XYNUI/

-----

Finally, it would be nice if there was a watcher which would invoke the codemod whenever your models changed,
which would ease development.