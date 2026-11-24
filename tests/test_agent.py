"""Tests for the AI agent module."""

import pytest

from Source.agent import BaseAgent, DeductiveAgent, HumanAgent, RandomAgent, create_agent
from Source.dpll import SATOracle
from Source.game_engine import GameEngine


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


def test_deductive_agent_solves_default_puzzle_and_trace_matches_initial_hidden_cards() -> None:
    """DeductiveAgent should solve the default puzzle and trace all initially hidden cards."""
    engine = GameEngine()
    initially_hidden = sum(1 for cell in engine.state.board.values() if not cell.get("is_revealed"))

    agent = DeductiveAgent(engine)
    result = agent.run()

    assert result == "SOLVED"
    assert len(agent.trace) == initially_hidden


def test_deductive_agent_trace_entries_have_required_keys() -> None:
    """Each trace entry should expose the expected fields for reporting and UI."""
    engine = GameEngine()
    agent = DeductiveAgent(engine)

    assert agent.run() == "SOLVED"

    required_keys = {
        "step",
        "wave",
        "active_clue_ids",
        "sat_queries",
        "character",
        "verdict",
        "revealed_clue",
        "revealed_clue_text",
    }

    assert agent.trace, "Trace should not be empty after solving the default puzzle."
    for item in agent.trace:
        assert required_keys.issubset(item.keys())


def test_deductive_agent_returns_timeout_when_oracle_deadline_is_immediate() -> None:
    """With timeout=0 from the SAT oracle, the deductive run should end with TIMEOUT."""
    engine = GameEngine()
    engine.oracle = SATOracle(timeout=0)

    agent = DeductiveAgent(engine)
    assert agent.run() == "TIMEOUT"


def test_deductive_agent_returns_stuck_on_underconstrained_puzzle_without_rejections() -> None:
    """A puzzle with insufficient clues should stop at STUCK and not produce rejected verdicts."""
    puzzle_data = {
        "size": 2,
        "cells": [
            {
                "id": "A1",
                "name": "A1",
                "status": "INNOCENT",
                "is_revealed": False,
            },
            {
                "id": "B1",
                "name": "B1",
                "status": "CRIMINAL",
                "is_revealed": False,
            },
            {
                "id": "A2",
                "name": "A2",
                "status": "CRIMINAL",
                "is_revealed": False,
            },
            {
                "id": "B2",
                "name": "B2",
                "status": "INNOCENT",
                "is_revealed": False,
            },
        ],
    }

    engine = GameEngine(puzzle_data=puzzle_data)
    agent = DeductiveAgent(engine)

    assert agent.run() == "STUCK"
    assert agent.terminal != "REJECTED"
    assert engine.state.last_action_result is None
    assert engine.state.verdicts == []
