import numpy as np
import pandas as pd

from lab.backtest import decide
from lab.data import load
from lab.jev_news import Judgment, news_vote
from lab.lenses import compute_lenses


def test_lenses_never_look_ahead():
    """Rösten vid bar i får inte ändras av att framtida bars läggs till.
    Om det här testet faller är backtestet värdelöst (det "ser" facit)."""
    df = load().iloc[:3000].reset_index(drop=True)
    full = compute_lenses(df)
    for cut in (800, 1500, 2999):
        partial = compute_lenses(df.iloc[: cut + 1])
        pd.testing.assert_series_equal(full.iloc[cut], partial.iloc[cut], check_names=False)


def test_decide_requires_share_of_all_lenses():
    votes = pd.DataFrame([[1] * 9 + [0], [1] * 8 + [0, 0], [-1] * 10])
    assert list(decide(votes, 0.9)) == [1, 0, -1]


def _j(rel, bull, bear, impact, opinion=0.0, recap=0.0):
    return Judgment("t", "s", "p", rel, bull, bear, 1 - bull - bear, 0.9, impact,
                    opinion, recap, "jev")


def test_news_vote_irrelevant_headlines_do_not_vote():
    assert news_vote([_j(0.05, 1.0, 0.0, 2.0)] * 3)[0] == 0


def test_news_vote_major_bearish_news_votes_down():
    vote, tilt = news_vote([_j(0.95, 0.05, 0.9, 2.0)])
    assert vote == -1 and tilt < -0.5


def test_news_vote_opposing_news_cancels():
    assert news_vote([_j(0.9, 0.9, 0.05, 1.0), _j(0.9, 0.05, 0.9, 1.0)])[0] == 0


def test_news_vote_opinions_and_recaps_do_not_vote():
    assert news_vote([_j(0.9, 1.0, 0.0, 2.0, opinion=0.95)] * 5)[0] == 0
    assert news_vote([_j(0.9, 1.0, 0.0, 2.0, recap=0.95)] * 5)[0] == 0


def test_news_vote_is_average_not_sum():
    """Många svaga rubriker åt samma håll får inte bli en stark röst."""
    one = news_vote([_j(0.9, 0.6, 0.4, 1.0)])[1]
    many = news_vote([_j(0.9, 0.6, 0.4, 1.0)] * 20)[1]
    assert many < 0.25 and many < one * 3
