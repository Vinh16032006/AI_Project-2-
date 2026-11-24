from Source.encoder import GameEncoder,decode_model,encode_game_state,encode_move
import pytest

def test_encoder_returns_list_of_clauses() -> None:
    clauses = encode_game_state({"board": []})

    assert isinstance(clauses, list)
    assert all(isinstance(clause, list) for clause in clauses)
    assert all(
        isinstance(literal, int) and not isinstance(literal, bool)
        and literal != 0
        for clause in clauses
        for literal in clause
    )

def test_move_encoder_returns_valid_clauses() -> None:
    clauses = encode_move(
        {"row": 0, "col": 0},
        {"board": []}
    )

    assert isinstance(clauses, list)
    assert all(isinstance(clause, list) for clause in clauses)
    assert all(
        isinstance(literal, int) and not isinstance(literal, bool)
        and literal != 0
        for clause in clauses
        for literal in clause
    )

def test_decode_model_works_with_empty_assignment() -> None:
    decoded = decode_model({})

    assert isinstance(decoded, dict)
    assert decoded == {}

def test_get_statistics_returns_correct_counts() -> None:
    from Source.encoder import GameEncoder

    encoder = GameEncoder()

    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }
    encoder.auxiliary_variable_map = {
        "aux_1": 3,
    }
    encoder.clauses = [
        [1, -2],
        [-1, 2],
        [1],
    ]

    statistics = encoder.get_statistics()

    assert statistics == {
        "primary_variables": 2,
        "auxiliary_variables": 1,
        "clauses": 3,
    }

def test_encode_fact_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {"Alice": 1}

    clauses = encoder.encode_clue({
        "type": "FACT",
        "character": "Alice",
        "status": "criminal",
    })

    assert clauses == [[1]]

def test_encode_same_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    clauses = encoder.encode_clue({
        "type": "SAME",
        "character1": "Alice",
        "character2": "Bob",
    })

    assert clauses == [
        [-1, 2],
        [1, -2],
    ]

def test_encode_different_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    clauses = encoder.encode_clue({
        "type": "DIFFERENT",
        "character1": "Alice",
        "character2": "Bob",
    })

    assert clauses == [
        [1, 2],
        [-1, -2],
    ]

def test_encode_exactly_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
        "Charlie": 3,
    }

    clauses = encoder.encode_clue({
        "type": "EXACTLY",
        "characters": ["Alice", "Bob", "Charlie"],
        "count": 2,
    })

    assert clauses == [
        [-1, -2, -3],
        [1, 2],
        [1, 3],
        [2, 3],
    ]

def test_encode_at_least_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
        "Charlie": 3,
    }

    clauses = encoder.encode_clue({
        "type": "AT_LEAST",
        "characters": ["Alice", "Bob", "Charlie"],
        "count": 2,
    })

    assert clauses == [
        [1, 2],
        [1, 3],
        [2, 3],
    ]

def test_encode_at_most_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
        "Charlie": 3,
    }

    clauses = encoder.encode_clue({
        "type": "AT_MOST",
        "characters": ["Alice", "Bob", "Charlie"],
        "count": 2,
    })

    assert clauses == [
        [-1, -2, -3],
    ]

def test_encode_exactly_zero_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    clauses = encoder.encode_clue({
        "type": "EXACTLY",
        "characters": ["Alice", "Bob"],
        "count": 0,
    })

    assert clauses == [
        [-1],
        [-2],
    ]

def test_encode_at_least_zero_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    clauses = encoder.encode_clue({
        "type": "AT_LEAST",
        "characters": ["Alice", "Bob"],
        "count": 0,
    })

    assert clauses == []

def test_encode_at_most_all_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    clauses = encoder.encode_clue({
        "type": "AT_MOST",
        "characters": ["Alice", "Bob"],
        "count": 2,
    })

    assert clauses == []

def test_encode_exactly_rejects_invalid_count() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    with pytest.raises(ValueError):
        encoder.encode_clue({
            "type": "EXACTLY",
            "characters": ["Alice", "Bob"],
            "count": 3,
        })

def test_encode_same_rejects_unknown_character() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
    }

    with pytest.raises(ValueError):
        encoder.encode_clue({
            "type": "SAME",
            "character1": "Alice",
            "character2": "Bob",
        })

def test_evaluate_fact_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {"Alice": 1}

    assert encoder.evaluate_clue(
        {
            "type": "FACT",
            "character": "Alice",
            "status": "criminal",
        },
        {1: True},
    ) is True

    assert encoder.evaluate_clue(
        {
            "type": "FACT",
            "character": "Alice",
            "status": "criminal",
        },
        {1: False},
    ) is False

def test_evaluate_same_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    clue = {
        "type": "SAME",
        "character1": "Alice",
        "character2": "Bob",
    }

    assert encoder.evaluate_clue(clue, {1: True, 2: True}) is True
    assert encoder.evaluate_clue(clue, {1: False, 2: False}) is True
    assert encoder.evaluate_clue(clue, {1: True, 2: False}) is False

def test_evaluate_different_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    clue = {
        "type": "DIFFERENT",
        "character1": "Alice",
        "character2": "Bob",
    }

    assert encoder.evaluate_clue(clue, {1: True, 2: False}) is True
    assert encoder.evaluate_clue(clue, {1: False, 2: True}) is True
    assert encoder.evaluate_clue(clue, {1: True, 2: True}) is False

def test_evaluate_exactly_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
        "Charlie": 3,
    }

    clue = {
        "type": "EXACTLY",
        "characters": ["Alice", "Bob", "Charlie"],
        "count": 2,
    }

    assert encoder.evaluate_clue(clue, {1: True, 2: True, 3: False}) is True
    assert encoder.evaluate_clue(clue, {1: True, 2: False, 3: False}) is False
    assert encoder.evaluate_clue(clue, {1: True, 2: True, 3: True}) is False

def test_evaluate_at_least_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
        "Charlie": 3,
    }

    clue = {
        "type": "AT_LEAST",
        "characters": ["Alice", "Bob", "Charlie"],
        "count": 2,
    }

    assert encoder.evaluate_clue(clue, {1: True, 2: True, 3: False}) is True
    assert encoder.evaluate_clue(clue, {1: True, 2: True, 3: True}) is True
    assert encoder.evaluate_clue(clue, {1: True, 2: False, 3: False}) is False

def test_evaluate_at_most_clue() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
        "Charlie": 3,
    }

    clue = {
        "type": "AT_MOST",
        "characters": ["Alice", "Bob", "Charlie"],
        "count": 2,
    }

    assert encoder.evaluate_clue(clue, {1: True, 2: True, 3: False}) is True
    assert encoder.evaluate_clue(clue, {1: True, 2: False, 3: False}) is True
    assert encoder.evaluate_clue(clue, {1: True, 2: True, 3: True}) is False

def test_evaluate_clue_rejects_missing_assignment() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }

    clue = {
        "type": "SAME",
        "character1": "Alice",
        "character2": "Bob",
    }

    with pytest.raises(ValueError):
        encoder.evaluate_clue(clue, {1: True})

def test_evaluate_clue_rejects_non_boolean_assignment() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {"Alice": 1}

    clue = {
        "type": "FACT",
        "character": "Alice",
        "status": "criminal",
    }

    with pytest.raises(ValueError):
        encoder.evaluate_clue(clue, {1: 1})

def test_encode_game_state_uses_only_revealed_clues() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice", "Bob"],
        "revealed_clues": [
            {
                "type": "FACT",
                "character": "Alice",
                "status": "criminal",
            }
        ],
        "unrevealed_clues": [
            {
                "type": "FACT",
                "character": "Bob",
                "status": "criminal",
            }
        ],
        "verdicts": [],
    }

    clauses = encoder.encode_game_state(game_state)

    assert clauses == [[1]]
    assert "Alice" in encoder.variable_map
    assert "Bob" in encoder.variable_map

def test_encode_game_state_adds_verdicts() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice", "Bob"],
        "revealed_clues": [],
        "verdicts": [
            {
                "character": "Alice",
                "status": "criminal",
            },
            {
                "character": "Bob",
                "status": "innocent",
            },
        ],
    }

    clauses = encoder.encode_game_state(game_state)

    assert clauses == [[1], [-2]]

def test_encode_game_state_ignores_hidden_status() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": [
            {
                "character": "Alice",
                "status": "criminal",
            },
            {
                "character": "Bob",
                "status": "innocent",
            },
        ],
        "revealed_clues": [],
        "verdicts": [],
    }

    clauses = encoder.encode_game_state(game_state)

    assert clauses == []
    assert encoder.variable_map == {
        "Alice": 1,
        "Bob": 2,
    }

def test_variable_map_is_deterministic() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice", "Bob", "Charlie"],
        "revealed_clues": [],
        "verdicts": [],
    }

    encoder.build_variable_map(game_state)
    first_mapping = encoder.variable_map.copy()

    encoder.build_variable_map(game_state)
    second_mapping = encoder.variable_map.copy()

    assert first_mapping == second_mapping
    assert first_mapping == {
        "Alice": 1,
        "Bob": 2,
        "Charlie": 3,
    }

def test_variable_map_does_not_duplicate_characters() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice", "Bob", "Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    encoder.build_variable_map(game_state)

    assert encoder.variable_map == {
        "Alice": 1,
        "Bob": 2,
    }
    assert len(encoder.variable_map) == 2

def test_variable_map_is_stable_across_dict_order() -> None:
    encoder_1 = GameEncoder()
    encoder_2 = GameEncoder()

    game_state_1 = {
        "board": {
            "A1": {"id": "A1"},
            "B1": {"id": "B1"},
            "A2": {"id": "A2"},
        },
        "revealed_clues": [],
        "verdicts": [],
    }

    game_state_2 = {
        "board": {
            "A2": {"id": "A2"},
            "A1": {"id": "A1"},
            "B1": {"id": "B1"},
        },
        "revealed_clues": [],
        "verdicts": [],
    }

    encoder_1.build_variable_map(game_state_1)
    encoder_2.build_variable_map(game_state_2)

    assert encoder_1.variable_map == encoder_2.variable_map
    assert encoder_1.variable_map == {
        "A1": 1,
        "B1": 2,
        "A2": 3,
    }

def test_decode_model_returns_character_assignments() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
        "Bob": 2,
    }
    encoder.reverse_variable_map = {
        1: "Alice",
        2: "Bob",
    }

    decoded = encoder.decode_model({
        1: True,
        2: False,
    })

    assert decoded == {
        "Alice": True,
        "Bob": False,
    }

def test_decode_model_ignores_auxiliary_variables() -> None:
    encoder = GameEncoder()
    encoder.variable_map = {
        "Alice": 1,
    }
    encoder.reverse_variable_map = {
        1: "Alice",
    }
    encoder.auxiliary_variable_map = {
        "aux_1": 2,
    }

    decoded = encoder.decode_model({
        1: True,
        2: False,
    })

    assert decoded == {
        "Alice": True,
    }

def test_encode_move_criminal() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice", "Bob"],
        "revealed_clues": [],
        "verdicts": [],
    }

    result = encoder.encode_move(
        {"character": "Alice", "status": "criminal"},
        game_state,
    )

    assert result == [[1]]


def test_encode_move_innocent() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice", "Bob"],
        "revealed_clues": [],
        "verdicts": [],
    }

    result = encoder.encode_move(
        {"character": "Bob", "status": "innocent"},
        game_state,
    )

    assert result == [[-2]]

def test_encode_move_without_character_and_status() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    assert encoder.encode_move({}, game_state) == []


def test_encode_move_rejects_missing_character() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    with pytest.raises(ValueError):
        encoder.encode_move({"status": "criminal"}, game_state)


def test_encode_move_rejects_missing_status() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    with pytest.raises(ValueError):
        encoder.encode_move({"character": "Alice"}, game_state)


def test_encode_move_rejects_unknown_character() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    with pytest.raises(ValueError):
        encoder.encode_move(
            {"character": "Bob", "status": "criminal"},
            game_state,
        )

def test_encode_move_rejects_invalid_status() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    with pytest.raises(ValueError):
        encoder.encode_move(
            {"character": "Alice", "status": "unknown"},
            game_state,
        )


def test_encode_move_rejects_non_string_non_boolean_status() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    with pytest.raises(ValueError):
        encoder.encode_move(
            {"character": "Alice", "status": 1},
            game_state,
        )

def test_encode_move_accepts_boolean_status() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    assert encoder.encode_move(
        {"character": "Alice", "status": True},
        game_state,
    ) == [[1]]

    assert encoder.encode_move(
        {"character": "Alice", "status": False},
        game_state,
    ) == [[-1]]

def test_encode_move_normalizes_status() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    assert encoder.encode_move(
        {"character": "Alice", "status": "  CRIMINAL  "},
        game_state,
    ) == [[1]]

def test_encode_move_normalizes_character() -> None:
    encoder = GameEncoder()

    game_state = {
        "board": ["Alice"],
        "revealed_clues": [],
        "verdicts": [],
    }

    assert encoder.encode_move(
        {"character": "  Alice  ", "status": "criminal"},
        game_state,
    ) == [[1]]