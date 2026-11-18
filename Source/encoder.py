from __future__ import annotations

from typing import Any, Dict, List


class GameEncoder:
    def __init__(self, game_state: Any | None = None) -> None:
        self.game_state = game_state
        self.variable_map: Dict[str, int] = {}
        self.reverse_variable_map: Dict[int, str] = {}
        self.auxiliary_variable_map: Dict[str, int] = {}
        self.clauses: List[List[int]] = []
        self.next_variable_id = 1

    def reset(self, game_state: Any | None = None) -> None:
        self.game_state = game_state
        self.variable_map.clear()
        self.reverse_variable_map.clear()
        self.auxiliary_variable_map.clear()
        self.clauses.clear()
        self.next_variable_id = 1

    def get_statistics(self) -> Dict[str, int]:
        return {
            "primary_variables": len(self.variable_map),
            "auxiliary_variables": len(self.auxiliary_variable_map),
            "clauses": len(self.clauses),
        }

    def register_variable(self, name: str, value: Any) -> int:
        if name in self.variable_map:
            return self.variable_map[name]
        variable_id = self.next_variable_id
        self.next_variable_id += 1
        self.variable_map[name] = variable_id
        self.reverse_variable_map[variable_id] = name
        return variable_id

    
    
    def build_variable_map(self, game_state: Any) -> None:
        self.reset(game_state)

        if isinstance(game_state, dict):
            board = game_state.get("board")
        else:
            board = getattr(game_state, "board", None)

        if board is None:
            raise ValueError("Game state does not contain a board.")

        def register_character(character: Any) -> None:
            if character is None:
                return

            if isinstance(character, dict):
                if "character" in character:
                    register_character(character["character"])
                    return

                identifier = character.get("id")
                if identifier is None:
                    identifier = character.get("name")

                if identifier is not None:
                    name = str(identifier).strip()
                    if name:
                        self.register_variable(name, None)
                    return

                if not any(key in character for key in ("id", "name")):
                    for value in character.values():
                        traverse_board(value)

                return

            if hasattr(character, "character"):
                register_character(character.character)
                return

            identifier = getattr(character, "id", None)
            if identifier is None:
                identifier = getattr(character, "name", None)

            if identifier is not None:
                name = str(identifier).strip()
                if name:
                    self.register_variable(name, None)
                return

            if isinstance(character, str):
                name = character.strip()
                if name:
                    self.register_variable(name, None)

        def traverse_board(cells: Any) -> None:
            if isinstance(cells, (list, tuple)):
                for cell in cells:
                    traverse_board(cell)
            elif isinstance(cells, dict):
                if any(key in cells for key in ("id", "name", "character")):
                    register_character(cells)
                else:
                    for value in cells.values():
                        traverse_board(value)
            else:
                register_character(cells)

        if not isinstance(board, (list, tuple, dict)):
            raise TypeError("Board must be a list, tuple, or dictionary.")

        traverse_board(board)
    
    def encode_game_state(self, game_state: Any) -> List[List[int]]:
        self.game_state = game_state

        def get_value(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        self.build_variable_map(game_state)
        self.clauses = []

        revealed_clues = get_value(game_state, "revealed_clues", [])
        verdicts = get_value(game_state, "verdicts", [])

        if not isinstance(revealed_clues, (list, tuple)):
            raise ValueError("revealed_clues must be a list or tuple.")

        if not isinstance(verdicts, (list, tuple)):
            raise ValueError("verdicts must be a list or tuple.")

        for clue in revealed_clues:
            self.clauses.extend(self.encode_clue(clue))

        for verdict in verdicts:
            character = get_value(verdict, "character")
            status = get_value(verdict, "status")

            if character is None:
                raise ValueError("Verdict must contain a character identifier.")

            character = str(character).strip()

            if character not in self.variable_map:
                raise ValueError(f"Unknown character in verdict: {character}")

            if isinstance(status, bool):
                is_criminal = status
            elif isinstance(status, str):
                normalized_status = status.strip().lower()

                if normalized_status in {"criminal", "guilty"}:
                    is_criminal = True
                elif normalized_status in {"innocent", "not guilty"}:
                    is_criminal = False
                else:
                    raise ValueError(f"Invalid verdict status: {status}")
            else:
                raise ValueError(f"Invalid verdict status: {status}")

            variable_id = self.variable_map[character]
            literal = variable_id if is_criminal else -variable_id

            self.clauses.append([literal])

        return self.clauses

    def encode_clue(self, clue: Any) -> List[List[int]]:
        def get_value(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        clue_type = get_value(clue, "type")

        if not isinstance(clue_type, str):
            raise ValueError("Clue type must be a string.")

        clue_type = clue_type.strip().upper()
        #Fact
        if clue_type == "FACT":
            character = get_value(clue, "character")

            if character is None:
                raise ValueError("FACT clue must specify a character.")

            character = str(character).strip()

            if character not in self.variable_map:
                raise ValueError(f"Unknown character: {character}")

            status = get_value(clue, "status")

            if isinstance(status, bool):
                is_criminal = status
            elif isinstance(status, str):
                normalized_status = status.strip().lower()

                if normalized_status in {"criminal", "guilty"}:
                    is_criminal = True
                elif normalized_status in {"innocent", "not guilty"}:
                    is_criminal = False
                else:
                    raise ValueError(f"Invalid FACT status: {status}")
            else:
                raise ValueError(f"Invalid FACT status: {status}")

            variable_id = self.variable_map[character]

            return [[variable_id if is_criminal else -variable_id]]
        #Same
        if clue_type == "SAME":
            character1 = get_value(clue, "character1")
            character2 = get_value(clue, "character2")

            if character1 is None or character2 is None:
                raise ValueError("SAME clue must specify two characters.")

            character1 = str(character1).strip()
            character2 = str(character2).strip()

            if character1 not in self.variable_map:
                raise ValueError(f"Unknown character: {character1}")

            if character2 not in self.variable_map:
                raise ValueError(f"Unknown character: {character2}")

            var1 = self.variable_map[character1]
            var2 = self.variable_map[character2]

            return [
                [-var1, var2],
                [var1, -var2]
                    ]
        #Different
        if clue_type == "DIFFERENT":
            character1 = get_value(clue, "character1")
            character2 = get_value(clue, "character2")

            if character1 is None or character2 is None:
                raise ValueError("DIFFERENT clue must specify two characters.")

            character1 = str(character1).strip()
            character2 = str(character2).strip()

            if character1 not in self.variable_map:
                raise ValueError(f"Unknown character: {character1}")

            if character2 not in self.variable_map:
                raise ValueError(f"Unknown character: {character2}")

            var1 = self.variable_map[character1]
            var2 = self.variable_map[character2]

            return [
                [var1, var2],
                [-var1, -var2]
            ]
        #Exactly
        if clue_type == "EXACTLY":
            from itertools import combinations

            characters = get_value(clue, "characters")
            k = get_value(clue, "count")

            if not isinstance(characters, (list, tuple)):
                raise ValueError("EXACTLY clue must contain a list of characters.")

            if not isinstance(k, int) or isinstance(k, bool):
                raise ValueError("EXACTLY count must be an integer.")

            names = [
                str(character).strip() if character is not None else ""
                for character in characters
            ]

            if any(not name for name in names):
                raise ValueError("Character identifiers cannot be empty.")

            if len(set(names)) != len(names):
                raise ValueError("Clue contains duplicate characters.")

            characters = names

            if k < 0 or k > len(characters):
                raise ValueError("EXACTLY count must be between 0 and region size.")

            variables = []

            for character in characters:
                character = str(character).strip()

                if character not in self.variable_map:
                    raise ValueError(f"Unknown character: {character}")

                variables.append(self.variable_map[character])

            clauses = []

            for group in combinations(variables, k + 1):
                clauses.append([-var for var in group])

            for group in combinations(variables, len(variables) - k + 1):
                clauses.append(list(group))

            return clauses
        #At_least
        if clue_type == "AT_LEAST":
            from itertools import combinations

            characters = get_value(clue, "characters")
            k = get_value(clue, "count")

            if not isinstance(characters, (list, tuple)):
                raise ValueError("AT_LEAST clue must contain a list of characters.")

            if not isinstance(k, int) or isinstance(k, bool):
                raise ValueError("AT_LEAST count must be an integer.")

            names = [
                str(character).strip() if character is not None else ""
                for character in characters
            ]

            if any(not name for name in names):
                raise ValueError("Character identifiers cannot be empty.")

            if len(set(names)) != len(names):
                raise ValueError("Clue contains duplicate characters.")

            characters = names

            if k < 0 or k > len(characters):
                raise ValueError("AT_LEAST count must be between 0 and region size.")

            variables = []

            for character in characters:
                character = str(character).strip()

                if character not in self.variable_map:
                    raise ValueError(f"Unknown character: {character}")

                variables.append(self.variable_map[character])

            clauses = []

            for group in combinations(variables, len(variables) - k + 1):
                clauses.append(list(group))

            return clauses
        #At_most
        if clue_type == "AT_MOST":
            from itertools import combinations

            characters = get_value(clue, "characters")
            k = get_value(clue, "count")

            if not isinstance(characters, (list, tuple)):
                raise ValueError("AT_MOST clue must contain a list of characters.")

            if not isinstance(k, int) or isinstance(k, bool):
                raise ValueError("AT_MOST count must be an integer.")

            names = [
                str(character).strip() if character is not None else ""
                for character in characters
            ]

            if any(not name for name in names):
                raise ValueError("Character identifiers cannot be empty.")

            if len(set(names)) != len(names):
                raise ValueError("Clue contains duplicate characters.")

            characters = names

            if k < 0 or k > len(characters):
                raise ValueError("AT_MOST count must be between 0 and region size.")

            variables = []

            for character in characters:
                character = str(character).strip()

                if character not in self.variable_map:
                    raise ValueError(f"Unknown character: {character}")

                variables.append(self.variable_map[character])

            clauses = []

            for group in combinations(variables, k + 1):
                clauses.append([-var for var in group])

            return clauses
        
        raise ValueError(f"Unsupported clue type: {clue_type}")

    def evaluate_clue(
        self,
        clue: Any,
        assignment: Dict[int, bool]
    ) -> bool:
        def get_value(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        clue_type = get_value(clue, "type")

        if not isinstance(clue_type, str):
            raise ValueError("Clue must have a valid type.")

        clue_type = clue_type.strip().upper()

        def get_status(character: Any) -> bool:
            if character is None:
                raise ValueError("Character identifier cannot be None.")
            
            character = str(character).strip()

            if not character:
                raise ValueError("Character identifier cannot be empty.")
    
            if character not in self.variable_map:
                raise ValueError(f"Unknown character: {character}")

            variable_id = self.variable_map[character]

            if variable_id not in assignment:
                raise ValueError(
                    f"Assignment is missing variable {variable_id}."
                )

            status = assignment[variable_id]

            if not isinstance(status, bool):
                raise ValueError(
                    f"Variable {variable_id} must have a Boolean value."
                )

            return status

        if clue_type == "FACT":
            character = get_value(clue, "character")
            status = get_value(clue, "status")

            if character is None:
                raise ValueError("FACT clue must specify a character.")

            if isinstance(status, bool):
                expected = status
            elif isinstance(status, str):
                normalized_status = status.strip().lower()

                if normalized_status in {"criminal", "guilty"}:
                    expected = True
                elif normalized_status in {"innocent", "not guilty"}:
                    expected = False
                else:
                    raise ValueError(f"Invalid FACT status: {status}")
            else:
                raise ValueError(f"Invalid FACT status: {status}")

            return get_status(character) == expected

        if clue_type in {"SAME", "DIFFERENT"}:
            character1 = get_value(clue, "character1")
            character2 = get_value(clue, "character2")

            if character1 is None or character2 is None:
                raise ValueError(
                    f"{clue_type} clue must specify two characters."
                )

            status1 = get_status(character1)
            status2 = get_status(character2)

            if clue_type == "SAME":
                return status1 == status2

            return status1 != status2

        if clue_type in {"EXACTLY", "AT_LEAST", "AT_MOST"}:
            characters = get_value(clue, "characters")
            k = get_value(clue, "count")

            if not isinstance(characters, (list, tuple)):
                raise ValueError(
                    f"{clue_type} clue must contain a list of characters."
                )

            if not isinstance(k, int) or isinstance(k, bool):
                raise ValueError("Clue count must be an integer.")

            names = [
                str(character).strip() if character is not None else ""
                for character in characters
            ]

            if any(not name for name in names):
                raise ValueError("Character identifiers cannot be empty.")

            if len(set(names)) != len(names):
                raise ValueError("Clue contains duplicate characters.")

            characters = names

            if k < 0 or k > len(characters):
                raise ValueError("Clue count is outside the valid range.")

            criminal_count = sum(
                get_status(character) for character in characters
            )

            if clue_type == "EXACTLY":
                return criminal_count == k

            if clue_type == "AT_LEAST":
                return criminal_count >= k

            return criminal_count <= k

        raise ValueError(f"Unsupported clue type: {clue_type}")

    def encode_move(self, move: Any, game_state: Any) -> List[List[int]]:
        if self.game_state is not game_state or not self.variable_map:
            self.build_variable_map(game_state)
        else:
            self.game_state = game_state
        def get_value(obj: Any, key: str, default: Any = None) -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        character = get_value(move, "character")
        status = get_value(move, "status")

        if character is None and status is None:
            return []

        if character is None:
            raise ValueError("Move must specify a character.")

        if status is None:
            raise ValueError("Move must specify a status.")
        character = str(character).strip()

        if not character:
            raise ValueError("Character identifier cannot be empty.")

        if character not in self.variable_map:
            raise ValueError(f"Unknown character: {character}")

        if isinstance(status, bool):
            is_criminal = status
        elif isinstance(status, str):
            normalized_status = status.strip().lower()

            if normalized_status in {"criminal", "guilty"}:
                is_criminal = True
            elif normalized_status in {"innocent", "not guilty"}:
                is_criminal = False
            else:
                raise ValueError(f"Invalid move status: {status}")
        else:
            raise ValueError(f"Invalid move status: {status}")

        variable_id = self.variable_map[character]

        literal = variable_id if is_criminal else -variable_id

        return [[literal]]
    
    def decode_model(self, model: Dict[int, bool]) -> Dict[str, bool]:

        if not isinstance(model, dict):
            raise TypeError("Model must be a dictionary.")

        decoded: Dict[str, bool] = {}

        for variable_id, value in model.items():
            if (
                not isinstance(variable_id, int)
                or isinstance(variable_id, bool)
                or variable_id <= 0
            ):
                raise ValueError("Variable ID must be a positive integer.")

            if not isinstance(value, bool):
                raise ValueError("Model values must be Boolean.")

            character = self.reverse_variable_map.get(variable_id)

            if character is not None:
                decoded[character] = value

        return decoded

def encode_game_state(game_state: Any) -> List[List[int]]:
    encoder = GameEncoder(game_state)
    return encoder.encode_game_state(game_state)


def encode_move(move: Any, game_state: Any) -> List[List[int]]:
    encoder = GameEncoder(game_state)
    return encoder.encode_move(move, game_state)

def decode_model(
    model: Dict[int, bool],
    encoder: GameEncoder | None = None
) -> Dict[str, bool]:
    if encoder is None:
        if not model:
            return {}

        raise ValueError(
            "An encoder instance is required to decode the model."
        )

    return encoder.decode_model(model)