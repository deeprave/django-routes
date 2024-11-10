#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Show all routes in a Django project
import sys
import os
import argparse
from pathlib import Path

import django_extensions.management.commands.show_urls
from django.core.exceptions import ViewDoesNotExist


def main():
    from django_settings_env import Env

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-r", "--root", default=None, help="Django root directory")
    parser.add_argument("-s", "--settings", default=None, help="Django settings module")
    parser.add_argument(
        "-c", "--color", action="store_true", help="Force Colourize output"
    )
    parser.add_argument(
        "-n", "--no-color", action="store_true", help="Force No Colourize output"
    )
    args = parser.parse_args()

    # determine where we are and look for django's root (where manage.py lives)

    project_root = Path.cwd()
    if args.root:
        django_root = Path(args.root).absolute()
    elif (project_root / "manage.py").exists():
        django_root = project_root
    else:
        manage_scripts = list(project_root.glob("*/manage.py"))
        if not manage_scripts:
            print(
                "Can't locate manage.py in current or any subdirectory", file=sys.stderr
            )
            exit(1)
        elif len(manage_scripts) > 1:
            print("Found multiple manage.py scripts", file=sys.stderr)
            exit(1)
        django_root = manage_scripts[0].parent
    os.chdir(django_root)
    django_root_str = str(django_root.absolute())

    env = Env(readenv=True, search_path=[django_root, django_root.parent], parents=True)
    if django_root_str not in sys.path:
        sys.path.insert(0, django_root_str)

    if args.settings:
        env.export({"DJANGO_SETTINGS_MODULE": args.settings})

    if "DJANGO_SETTINGS_MODULE" not in os.environ:
        print(
            "DJANGO_SETTINGS_MODULE is not set nor --settings provided", file=sys.stderr
        )
        exit(1)

    color_enabled = (
        True if args.color else False if args.no_color else sys.stdout.isatty()
    )

    # now we can import django etc.
    from importlib import import_module

    import django
    from django.conf import settings
    from django.urls import URLPattern, URLResolver

    django.setup(set_prefix=False)

    root_urlconf = import_module(settings.ROOT_URLCONF)

    def with_colors(text, **kwargs) -> str:
        from django.utils.termcolors import colorize

        if color_enabled:
            text = colorize(text, **kwargs)
        return text

    def traverse(url_patterns, prefix="", namespace=None, indent=0):
        indent_space = "\t" * indent
        for p in url_patterns:
            composed = f"{prefix}{p.pattern}"
            if namespace:
                composed = f"{namespace}:{composed}"
            if isinstance(
                p,
                (
                    URLPattern,
                    django_extensions.management.commands.show_urls.RegexURLPattern,
                ),
            ):
                name = f" ({p.name})" if p.name else ""
                print(with_colors(f"{indent_space}{composed}", fg="green"), "=> ", end="")
                # sourcery skip: use-contextlib-suppress
                try:
                    print(with_colors(f"{p.callback.__module__}.", fg="yellow"), end="")
                    print(f"{p.callback.view_class.__name__}", end="")
                    print(with_colors(name, fg="white"))
                    continue
                except AttributeError:
                    pass
                try:
                    print(p.callback.cls.__name__, end="")
                    print(with_colors(name, fg="white"))
                except AttributeError:
                    print(p.callback.__name__, end="")
                    print(with_colors(name, fg="white"))
            elif isinstance(
                p,
                (
                    URLResolver,
                    django_extensions.management.commands.show_urls.RegexURLResolver,
                ),
            ):
                print(with_colors(f"{indent_space}{composed[:-1]} [", fg="blue"))
                traverse(p.url_patterns, prefix=composed, indent=indent + 1)
                print(with_colors(f"{indent_space}]", fg="blue"))
            elif hasattr(p, "_get_callback"):
                try:
                    print(
                        with_colors(f"{indent_space}{composed}", fg="green"),
                        "=> ",
                        end="",
                    )
                except ViewDoesNotExist:
                    continue
            elif hasattr(p, "url_patterns") or hasattr(p, "_get_url_patterns"):
                try:
                    patterns = p.url_patterns
                except ImportError:
                    continue
                print(with_colors(f"{indent_space}{composed}", fg="green"), "=> ", end="")
                traverse(
                    patterns, prefix=composed, namespace=namespace, indent=indent + 1
                )
            else:
                print(with_colors(f"unknown url pattern: {p}", fg="red"))

    traverse(root_urlconf.urlpatterns)


if __name__ == "__main__":
    main()
