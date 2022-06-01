import numpy as np
from ._common import (_all_indices, _order_tiebreak_keep, _random_tiebreak,
                      _no_tiebreak)
from .condorcet import condorcet_from_matrix

_tiebreak_map = {'order': _order_tiebreak_keep,
                 'random': _random_tiebreak,
                 None: _no_tiebreak}


def _get_tiebreak(tiebreaker):
    try:
        return _tiebreak_map[tiebreaker]
    except KeyError:
        raise ValueError('Tiebreaker not understood')


def matrix_from_scores(election):
    """
    Convert a scored ballot election to a pairwise comparison matrix.

    Parameters
    ----------
    election : array_like
        A 2D collection of score ballots.

        Rows represent voters, and columns represent candidate IDs.
        A cell contains a high score if that voter approves of that candidate,
        or low score if they disapprove.

    Returns
    -------
    matrix : ndarray
        A pairwise comparison matrix of candidate vs candidate defeats.

        For example, a ``3`` in row 2, column 5, means that 3 voters preferred
        Candidate 2 over Candidate 5.  Candidates are not preferred over
        themselves, so the diagonal is all zeros.

    Examples
    --------
    Voter 0 loves Candidates A (index 0) and B (index 1), but hates C (2).
    Voter 1 dislikes A, likes B, and loves C.
    Voter 2 hates A, is lukewarm about B and likes C.

    >>> election = [[5, 5, 0],
                    [0, 4, 5],
                    [0, 3, 4]]

    So, candidate B is preferred over A by 2 voters, while one is indifferent
    between them.  C is preferred over A by 2 voters, while A is preferred
    over C by 1 voter.  C is preferred over B by 2 voters, while B is preferred
    over C by 1 voter.

    >>> matrix_from_scores(election)
    array([[0, 0, 1],
           [2, 0, 1],
           [2, 2, 0]])

    """
    # Add extra dimensions so that election is broadcast against itself,
    # producing every combination of candidate pairs. Count how often each
    # beats the other.
    gt = np.expand_dims(election, 2) > np.expand_dims(election, 1)

    # Sum across all voters
    return gt.sum(axis=0)


def _pairwise_compare(election, a, b):
    """
    Find more-preferred candidate between `a` and `b` in `election`.

    Parameters
    ----------
    election : array_like
        A 2D collection of score ballots.
    a, b : int
        Indices of candidates.

    Returns
    -------
    winner : {a, b, None}
        Index of candidate who beats the other, or None if there is a tie.

    """
    a_beats_b = (election[:, a] > election[:, b]).sum()
    b_beats_a = (election[:, b] > election[:, a]).sum()
    if a_beats_b > b_beats_a:
        return a
    elif b_beats_a > a_beats_b:
        return b
    else:
        return None


def _scorewise_compare(tallies, a, b):
    """
    Find higher-scored candidate between `a` and `b` in `election`.

    Parameters
    ----------
    tallies : array_like
        A 1D collection of tallies of scores
    a, b : int
        Indices of candidates.

    Returns
    -------
    winner : {a, b, None}
        Index of candidate who beats the other, or None if there is a tie.

    """
    if tallies[a] > tallies[b]:
        return a
    elif tallies[b] > tallies[a]:
        return b
    else:
        return None


def star(election, tiebreaker=None):
    """
    Find the winner of an election using STAR voting.

    The more-preferred of the two highest-scoring candidates wins.[1]_

    Parameters
    ----------
    election : array_like
        A 2D collection of score ballots.

        Rows represent voters, and columns represent candidate IDs.
        A cell contains a high score if that voter approves of that candidate,
        or low score if they disapprove.

    tiebreaker : {'random', 'order', None}, optional
        If there is a tie, and `tiebreaker` is ``'random'``, a random finalist
        is returned.
        If 'order', the lowest-ID tied candidate is returned.
        By default, ``None`` is returned for ties.

    Returns
    -------
    winner : int
        The ID number of the winner, or ``None`` for an unbroken tie.

    Notes
    -----
    If there is a tie during the automatic runoff (neither candidate is
    preferred more than the other) then it is broken in favor of the
    higher-scoring candidate.

    If there is still a tie, it is broken according to the
    `tiebreaker` parameter.

    References
    ----------
    .. [1] https://en.wikipedia.org/wiki/STAR_voting
    .. [2] https://www.starvoting.us/ties

    Examples
    --------
    Voter 0 loves Candidates A (index 0) and B (index 1), but hates C (2).
    Voter 1 dislikes A, likes B, and loves C.
    Voter 2 hates A, is lukewarm about B and likes C.

    >>> election = [[5, 5, 0],
                    [0, 4, 5],
                    [0, 3, 4]]

    Candidates B and C (1 and 2) get the highest scores (12 and 9).  Of these,
    C is preferred on more ballots, and wins the election:

    >>> star(election)
    2

    """
    election = np.asarray(election)

    if election.min() < 0:
        raise ValueError

    if election.shape[1] == 1:
        # Only 1 candidate: that candidate wins.
        return 0

    # TODO: Follow the official tie-breaking rules
    # Break any True Ties using specified method
    tiebreak = _get_tiebreak(tiebreaker)

    # SCORING ROUND

    # Tally all scores
    tallies = election.sum(axis=0)

    # Find the set of candidates who have the highest score (usually only one)
    highest = max(tallies)
    first_set = _all_indices(tallies, highest)

    if len(first_set) == 2:
        first, second = first_set
    elif len(first_set) > 2:
        result = tiebreak(first_set, 2)
        if result[0] is None:
            return None
        else:
            first, second = result
    elif len(first_set) == 1:
        # One candidate has highest score
        first = first_set[0]
        # Find the set of candidates who have the second-highest score
        second = np.sort(tallies)[-2]
        second_set = _all_indices(tallies, second)
        if len(second_set) == 1:
            # One candidate has second-highest score. They go to runoff.
            second = second_set[0]
        else:
            # Two or more candidates have second-highest score.
            # "2. Ties in the Scoring round should be broken in favor of the
            # candidate who was preferred head-to-head by more voters."
            # "3. Multi-candidate ties in either round are broken in favor of
            # the Condorcet winner if one exists"
            matrix = matrix_from_scores(election[:, second_set])
            winner = condorcet_from_matrix(matrix)
            if winner is None:
                # There was still a tie or cycle.
                # '5. Ties which can not be broken as above are considered a
                # "True Tie."' "True ties can be broken by random selection."
                second = tiebreak(second_set, 1)[0]
            else:
                # There was a Condorcet winner among the tied candidates.
                # Map back to their original index.
                second = second_set[winner]
        if second is None:
            return None
    else:
        raise RuntimeError('This should not happen')

    # RUNOFF ROUND

    winner = _pairwise_compare(election, first, second)
    if winner is None:  # Neither candidate preferred over the other
        # "1. Ties in the Runoff round should be broken in favor of the
        # candidate who was scored higher if possible."
        winner = _scorewise_compare(tallies, first, second)
        if winner is None:  # Tied in both scores and preferences
            # '5. Ties which can not be broken as above are considered a "True
            # Tie."' "True ties can be broken by random selection."
            winner = tiebreak({first, second}, 1)[0]

    return winner
