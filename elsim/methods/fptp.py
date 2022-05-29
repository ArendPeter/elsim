import random
import numpy as np
from ._common import _all_indices


def _order_tiebreak_keep(winners, n=1):
    """
    Given an iterable of possibly tied `winners`, select the lowest-numbered
    `n` candidates.  If `n` is larger than `winners`, it is returned unchanged.
    """
    return sorted(winners)[:n]


def _random_tiebreak(winners, n=1):
    """
    Given an iterable of possibly tied `winners`, select `n` candidates at
    random.  If `n` is larger than `winners`, it is returned unchanged.
    """
    if len(winners) <= n:
        return winners
    else:
        return random.sample(winners, n)


def _no_tiebreak(winners, n=1):
    """
    Given an iterable of possibly tied `winners`, return None if there are more
    than `n` tied.  If `n` is larger than `winners`, it is returned unchanged.
    """
    if len(winners) <= n:
        return winners
    else:
        return [None]


_tiebreak_map = {'order': _order_tiebreak_keep,
                 'random': _random_tiebreak,
                 None: _no_tiebreak}


def _get_tiebreak(tiebreaker):
    try:
        return _tiebreak_map[tiebreaker]
    except KeyError:
        raise ValueError('Tiebreaker not understood')


def fptp(election, tiebreaker=None):
    """
    Find the winner of an election using first-past-the-post / plurality rule.

    The candidate with the largest number of first preferences wins.[1]_

    Parameters
    ----------
    election : array_like
        A 2D collection of ranked ballots.  (See `borda` for election format.)
        Or a 1D array of first preferences only.
    tiebreaker : {'random', 'order', None}, optional
        If there is a tie, and `tiebreaker` is ``'random'``, a random finalist
        is returned.
        If 'order', the lowest-ID tied candidate is returned.
        By default, ``None`` is returned for ties.

    Returns
    -------
    winner : int
        The ID number of the winner, or ``None`` for an unbroken tie.

    References
    ----------
    .. [1] https://en.wikipedia.org/wiki/Plurality_voting

    Examples
    --------
    Label some candidates:

    >>> A, B, C = 0, 1, 2

    Specify the ballots for the 5 voters:

    >>> election = [[A, C, B],
                    [A, C, B],
                    [B, A, C],
                    [B, C, A],
                    [B, C, A],
                    [C, A, B],
                    ]

    Candidate B (1) gets the most first-preference votes, and is the winner:

    >>> fptp(election)
    1

    Single-mark ballots can also be tallied (with ties broken as specified):

    >>> election = [A, B, B, C, C]
    >>> print(fptp(election))
    None

    There is a tie between B (1) and C (2).  ``tiebreaker=order`` always
    prefers the lower-numbered candidate in a tie:

    >>> fptp(election, 'order')
    1
    """
    election = np.asarray(election)

    # Tally all first preferences (with index of tally = candidate ID)
    if election.ndim == 2:
        first_preferences = election[:, 0]
    elif election.ndim == 1:
        first_preferences = election
    else:
        raise ValueError('Election array must be 2D ranked ballots or 1D'
                         'list of first preferences')
    tallies = np.bincount(first_preferences).tolist()

    # Find the set of candidates who have the highest score (usually only one)
    highest = max(tallies)
    winners = _all_indices(tallies, highest)

    # Break any ties using specified method
    tiebreak = _get_tiebreak(tiebreaker)
    return tiebreak(winners)[0]
