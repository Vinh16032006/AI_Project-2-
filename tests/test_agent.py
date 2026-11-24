"""Tests for the AI agent module."""

import pytest

from Source.agent import BaseAgent, HumanAgent, RandomAgent, create_agent


class DummyState:
    """Minimal state object that exposes legal moves in common shapes."""

    def __init__(self, moves):
        self.legal_moves = list(moves)

    def get_valid_moves(self):
        return list(self.legal_moves)


def test_agent_factory_returns_expected_types() -> None:
    """Validate that the factory creates the correct agent subclasses."""
    assert isinstance(create_agent("human"), HumanAgent)
    assert isinstance(create_agent("player"), HumanAgent)
    assert isinstance(create_agent("random"), RandomAgent)
    assert isinstance(create_agent("rand"), RandomAgent)


def test_agent_factory_rejects_unknown_strategy() -> None:
    """Unknown strategy names should raise a clear ValueError."""
    with pytest.raises(ValueError):
        create_agent("minimax")


def test_base_agent_is_abstract() -> None:
    """BaseAgent should not be instantiable directly."""
    try:
        BaseAgent(name="invalid")
    except TypeError:
        return
    assert False, "BaseAgent should be abstract and reject direct instantiation."


def test_random_agent_chooses_legal_move() -> None:
    """The random policy should choose from valid moves only."""
    state = DummyState(["up", "down", "left"])
    agent = RandomAgent(name="Random")
    move = agent.choose_move(state)
    assert move in state.legal_moves


def test_random_agent_requires_legal_move() -> None:
    """The random policy should fail gracefully when no legal moves exist."""
    agent = RandomAgent(name="Random")
    with pytest.raises((AttributeError, ValueError)):
        agent.choose_move(DummyState([]))
    with pytest.raises((AttributeError, ValueError)):
        agent.choose_move(state=None)


def test_human_agent_uses_input_handler() -> None:
    """HumanAgent should ask the provided input handler for a move."""
    state = DummyState(["left", "right"])
    agent = HumanAgent(name="Human", input_handler=lambda moves: "right")
    assert agent.choose_move(state) == "right"
