"""Tests for the CNF encoder."""

from Source.encoder import decode_model, encode_game_state, encode_move


def test_encoder_returns_list_of_clauses() -> None:
    """The encoder is expected to return a CNF-style list of clauses."""
    clauses = encode_game_state({"board": []})
    assert isinstance(clauses, list)


def test_move_encoder_returns_valid_clauses() -> None:
    """Move encoding should produce a list of CNF clauses or an empty list."""
    clauses = encode_move({"row": 0, "col": 0}, {"board": []})
    assert isinstance(clauses, list)


def test_decode_model_works_with_empty_assignment() -> None:
    """Decoding an empty model should produce an empty dictionary."""
    assert decode_model({}) == {}
