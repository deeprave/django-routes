#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from django.core.exceptions import ViewDoesNotExist
from django_extensions.management.commands.show_urls import RegexURLResolver, RegexURLPattern


def main():
    from pathlib import Path
    import sys
    from django_settings_env import Env

    # determine where we are and look for django's root (where manage.py lives)
    project_root = Path.cwd()
    if (project_root / 'manage.py').exists():
        django_root = project_root.as_posix()
    else:
        manage_scripts = [script for script in project_root.glob('*/manage.py')]
        if not manage_scripts:
            print('Can\'t locate manage.py in current or any subdirectory', file=sys.stderr)
            exit(1)
        elif len(manage_scripts) > 1:
            print('Found multiple manage.py scripts', file=sys.stderr)
            exit(1)
        django_root = manage_scripts[0].parent
    django_root_str = django_root.as_posix()
    if django_root_str not in sys.path:
        sys.path.append(django_root_str)
    env = Env(readenv=True, search_path=[django_root, django_root.parent], parents=True)
    env.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

    # how we can import django et al
    import django
    from django.conf import settings
    from django.urls import URLResolver, URLPattern
    from django.utils.termcolors import colorize
    from importlib import import_module

    django.setup(set_prefix=False)

    root_urlconf = import_module(settings.ROOT_URLCONF)

    def traverse(url_patterns, prefix='', namespace=None, indent=0):
        indent_space = '\t' * indent
        for p in url_patterns:
            composed = f'{prefix}{p.pattern}'
            if namespace:
                composed = f'{namespace}:{composed}'
            if isinstance(p, (URLPattern, RegexURLPattern)):
                name = f' ({p.name})' if p.name else ''
                print(colorize(f'{indent_space}{composed}', fg='green'), '=> ', end='')
                try:
                    print(colorize(f'{p.callback.__module__}.', fg='yellow'), end='')
                    print(f'{p.callback.view_class.__name__}', end='')
                    print(colorize(name, fg='white'))
                    continue
                except AttributeError:
                    pass
                try:
                    print(p.callback.cls.__name__, end='')
                    print(colorize(name, fg='white'))
                except AttributeError:
                    print(p.callback.__name__, end='')
                    print(colorize(name, fg='white'))
            elif isinstance(p, (URLResolver, RegexURLResolver)):
                print(colorize(f'{indent_space}{composed[:-1]} [', fg='blue'))
                traverse(p.url_patterns, prefix=composed, indent=indent+1)
                print(colorize(f'{indent_space}]', fg='blue'))
            elif hasattr(p, '_get_callback'):
                try:
                    print(colorize(f'{indent_space}{composed}', fg='green'), '=> ', end='')
                except ViewDoesNotExist:
                    continue
            elif hasattr(p, 'url_patterns') or hasattr(p, '_get_url_patterns'):
                try:
                    patterns = p.url_patterns
                except ImportError:
                    continue
                print(colorize(f'{indent_space}{composed}', fg='green'), '=> ', end='')
                traverse(patterns, prefix=composed, namespace=namespace, indent=indent+1)
            else:
                print(colorize(f'unknown url pattern: {p}', fg='red'))

    traverse(root_urlconf.urlpatterns)


if __name__ == '__main__':
    main()
