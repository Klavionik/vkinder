import os.path

import click

from vkinder import app
from vkinder import dbpath, tokenpath
from vkinder import menu


@click.version_option(prog_name='VKinder')
@click.option('--debug', '-d', is_flag=True, help='Enable API logging')
@click.option('--export', '-e', is_flag=True,
              help="Export next matches to a JSON file rather than printing to the console")
@click.option('--output', '-o', default=10, show_default=True,
              help="Amount of matches returned by 'next' menu option")
@click.group()
@click.pass_context
def cli(ctx, output, export, debug):
    """
    VKinder: Python coursework by Roman Vlasenko
    """
    ctx.ensure_object(dict)
    ctx.obj['output_amount'] = output
    ctx.obj['export'] = export
    ctx.obj['debug'] = debug


@cli.command()
@click.option('--same-sex', '-s', is_flag=True,
              help='Search for matches with the same sex as the set user')
@click.option('--ignore', '-i',
              type=click.Choice(('city', 'age'), case_sensitive=False), multiple=True,
              help='Ignore city and/or age when searching for matches')
@click.pass_context
def run(ctx, ignore, same_sex):
    """Start application and run menu"""
    if 'age' in ignore:
        ctx.obj['ignore_age'] = True
    if 'city' in ignore:
        ctx.obj['ignore_city'] = True
    ctx.obj['same_sex'] = same_sex
    vkinder = app.startup(ctx.obj)
    menu.run(vkinder)


@cli.command()
def cleardb():
    """Delete database file"""
    if os.path.exists(dbpath):
        os.remove(dbpath)


@cli.command()
def cleartoken():
    """Delete saved token"""
    if os.path.exists(tokenpath):
        os.remove(tokenpath)


if __name__ == '__main__':
    cli()
