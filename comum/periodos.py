"""Períodos de análise (usado por todos os relatórios): dia, semana (segunda a domingo), mês e ano, e como compará-los."""
import pandas as pd

GRANULARIDADES = ("D", "W", "M", "Y")
# quantos períodos entram nas tabelas de tendência (a linha mostra só os últimos N escolhidos na tela)
JANELA = {"D": 31, "W": 26, "M": 24, "Y": 10}


def inicio(dias: pd.Series, g: str) -> pd.Series:
    """Primeiro dia do período a que cada dia pertence."""
    d = dias.dt.normalize()
    if g == "D":
        return d
    if g == "W":
        return d - pd.to_timedelta(d.dt.weekday, unit="D")
    if g == "M":
        return d.dt.to_period("M").dt.start_time
    return d.dt.to_period("Y").dt.start_time


def fim(ini, g: str) -> pd.Timestamp:
    ini = pd.Timestamp(ini)
    if g == "D":
        return ini
    if g == "W":
        return ini + pd.Timedelta(days=6)
    if g == "M":
        return ini + pd.offsets.MonthEnd(0)
    return pd.Timestamp(year=ini.year, month=12, day=31)


def anterior(ini, g: str) -> pd.Timestamp:
    ini = pd.Timestamp(ini)
    return {"D": ini - pd.Timedelta(days=1), "W": ini - pd.Timedelta(days=7),
            "M": ini - pd.offsets.MonthBegin(1), "Y": ini - pd.DateOffset(years=1)}[g]


def ano_passado(ini, g: str) -> pd.Timestamp:
    """Mesmo período um ano antes (semana: 52 semanas antes, para cair na mesma segunda-feira)."""
    ini = pd.Timestamp(ini)
    return ini - pd.Timedelta(weeks=52) if g == "W" else ini - pd.DateOffset(years=1)


def rotulo(ini, g: str) -> str:
    """Nome completo do período, para as listas e títulos."""
    ini = pd.Timestamp(ini)
    if g == "D":
        return ini.strftime("%d/%m/%Y")
    if g == "W":
        f = fim(ini, g)
        return f"S{ini.isocalendar().week:02d} ({ini:%d/%m} – {f:%d/%m/%Y})"
    if g == "M":
        return ini.strftime("%m/%Y")
    return ini.strftime("%Y")


def rotulo_curto(ini, g: str, com_ano: bool = False) -> str:
    """Nome curto, para cabeçalho de coluna. com_ano=True quando o mesmo nome apareceria em anos diferentes."""
    ini = pd.Timestamp(ini)
    if g == "D":
        return ini.strftime("%d/%m/%y" if com_ano else "%d/%m")
    if g == "W":
        return f"S{ini.isocalendar().week:02d}" + (f"/{ini.isocalendar().year % 100:02d}" if com_ano else "")
    if g == "M":
        return ini.strftime("%m/%Y")
    return ini.strftime("%Y")


def lista(dias: pd.Series, g: str) -> list:
    """Períodos que existem nos dados, do mais antigo ao mais recente."""
    return sorted(inicio(dias, g).dropna().unique())


def completos(primeiro, ultimo, g: str) -> pd.DatetimeIndex:
    """Todos os períodos entre o primeiro e o último (inclusive), mesmo os sem dado: assim o gráfico mostra a lacuna."""
    passo = {"D": "D", "W": "7D", "M": "MS", "Y": "YS"}[g]
    return pd.date_range(pd.Timestamp(primeiro), pd.Timestamp(ultimo), freq=passo)
