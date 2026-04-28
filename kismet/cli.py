import sys

import click

from kismet.config import load_config


def _get_agent():
    try:
        config = load_config()
    except ValueError as e:
        click.echo(f"Configuration error: {e}", err=True)
        sys.exit(1)
    from kismet.agent.agent import KismetAgent
    return KismetAgent(config)


@click.group()
def cli():
    """KISMET — 業力引發哈希挖礦暨驅魔工具"""


@cli.command()
def commit():
    """全自動：占卜 → 視 K-value 決定是否改運 → commit"""
    _get_agent().run_commit()


@cli.command()
def divine():
    """只做占卜，輸出 K-value 和塔羅解讀（不 commit）"""
    _get_agent().run_divine()


@cli.command()
@click.argument("targets", nargs=-1)
def mine(targets):
    """只做逆天改運，找吉利 hash（不 commit）

    TARGETS: 指定吉利字串（空白分隔），例如：kismet mine 888 168
    不指定則使用預設吉利清單（888/168/777/666/連號/回文）
    """
    _get_agent().run_mine(list(targets))


@cli.command()
def force():
    """強制 commit（含驅魔儀式，跳過占卜與改運）"""
    _get_agent().run_force()


@cli.command()
@click.argument("targets", nargs=-1)
def curse(targets):
    """[下蠱模式] 反向挖礦，找不詳 hash 才 commit

    TARGETS: 指定不詳字串，例如：kismet curse dead 404
    不指定則使用預設不詳清單（dead/404/f00d/bad）
    """
    _get_agent().run_curse(list(targets))
