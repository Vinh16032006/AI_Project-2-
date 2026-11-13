"""Tests for the AI agent module."""

from Source.agent import BaseAgent, HumanAgent, RandomAgent, create_agent


def test_agent_factory_returns_expected_types() -> None:
    """Validate that the factory creates the correct agent subclasses."""
    assert isinstance(create_agent("human"), HumanAgent)
    assert isinstance(create_agent("random"), RandomAgent)


def test_base_agent_is_abstract() -> None:
    """BaseAgent should not be instantiable directly."""
    try:
        BaseAgent(name="invalid")
    except TypeError:
        return
    assert False, "BaseAgent should be abstract and reject direct instantiation."


def test_random_agent_requires_legal_move() -> None:
    """The random policy should fail gracefully when no legal moves exist."""
    agent = RandomAgent(name="Random")
    try:
        agent.choose_move(state=None)
    except (AttributeError, ValueError):
        return
    assert False, "RandomAgent should raise when no legal move is available."
