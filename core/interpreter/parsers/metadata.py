from typing import List, Optional, Tuple
from core.paths import Paths
from core.models.structures import MetadataPackage

class MetadataError(Exception):
    pass

class Metadata:
    @staticmethod
    def extract(metadata_line: str) -> MetadataPackage:
        package = MetadataPackage()
        if not metadata_line:
            return package

        position = 0
        total_length = len(metadata_line)

        while position < total_length:
            char = metadata_line[position]

            if char.isspace():
                position += 1
                continue

            if char == '(':
                group_content, position = Metadata._read_nested_group(metadata_line, position, '(', ')')
                Metadata._parse_directives_into_package(group_content, package)
                continue

            if char == '[':
                if package.logic is not None:
                    raise MetadataError("METADATA_ERROR: Multiple logic blocks [where] detected in a single command.")

                group_content, position = Metadata._read_nested_group(metadata_line, position, '[', ']')
                package.logic, package.logic_inversion = Metadata._parse_logic_clause(group_content)
                continue

            raise MetadataError(f"METADATA_ERROR: Unexpected character '{char}' at position {position}.")

        return package

    @staticmethod
    def _read_nested_group(text: str, start_pos: int, open_char: str, close_char: str) -> Tuple[str, int]:
        depth = 0
        current_idx = start_pos
        length = len(text)

        while current_idx < length:
            char = text[current_idx]

            if char == '"':
                current_idx += 1
                while current_idx < length and text[current_idx] != '"':
                    if text[current_idx] == '\\' and current_idx + 1 < length:
                        current_idx += 2
                        continue
                    current_idx += 1
                if current_idx >= length:
                    raise MetadataError("METADATA_ERROR: Unterminated string literal inside metadata group.")
                current_idx += 1
                continue

            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
                if depth == 0:
                    return text[start_pos + 1 : current_idx], current_idx + 1

            current_idx += 1

        raise MetadataError(f"METADATA_ERROR: Unclosed group. Expected '{close_char}' to match '{open_char}'.")

    @staticmethod
    def _tokenize_content(content: str) -> List[Tuple[str, str]]:
        tokens = []
        idx = 0
        length = len(content)

        while idx < length:
            char = content[idx]

            if char.isspace():
                idx += 1
                continue
            if char == '!':
                tokens.append(('BANG', '!'))
                idx += 1
            elif char == ',':
                tokens.append(('COMMA', ','))
                idx += 1
            elif char == ':':
                tokens.append(('COLON', ':'))
                idx += 1
            elif char == '"':
                idx += 1
                val = ""
                while idx < length and content[idx] != '"':
                    if content[idx] == '\\' and idx + 1 < length:
                        val += content[idx + 1]
                        idx += 2
                        continue
                    val += content[idx]
                    idx += 1
                if idx >= length:
                    raise MetadataError("METADATA_ERROR: Unterminated string inside directive.")
                idx += 1
                tokens.append(('STRING', val))
            else:
                start = idx
                while idx < length and content[idx] not in ' \t\n\r,:!"':
                    idx += 1
                tokens.append(('WORD', content[start:idx]))

        return tokens

    @staticmethod
    def _parse_directives_into_package(content: str, package: MetadataPackage):
        tokens = Metadata._tokenize_content(content)
        idx = 0
        token_count = len(tokens)

        while idx < token_count:
            kind, value = tokens[idx]

            if kind == 'BANG':
                idx += 1
                while idx < token_count and tokens[idx][0] == 'STRING':
                    package.exclusions.append(Paths.clean(tokens[idx][1]))
                    idx += 1
                    if idx < token_count and tokens[idx][0] == 'COMMA':
                        idx += 1
                        continue
                    break
                continue

            if kind == 'WORD':
                key = value.lower()
                if idx + 1 < token_count and tokens[idx + 1][0] == 'COLON':
                    if idx + 2 >= token_count or tokens[idx + 2][0] not in ('STRING', 'WORD'):
                        raise MetadataError(f"METADATA_ERROR: Directive '{key}' requires a value.")

                    raw_val = tokens[idx + 2][1]
                    idx += 3

                    if key == 'limit': package.limit = Metadata._to_int(key, raw_val)
                    elif key == 'depth': package.depth = Metadata._to_int(key, raw_val)
                    elif key == 'expires': package.expires = Metadata._to_int(key, raw_val)
                    elif key == 'level': package.level = Metadata._to_int(key, raw_val)
                    elif key == 'chunk': package.chunk_size = Metadata._to_int(key, raw_val)
                    elif key == 'workers': package.workers = Metadata._to_int(key, raw_val)
                    elif key == 'timeout': package.task_timeout = Metadata._to_int(key, raw_val)
                    elif key == 'tier': package.tier = raw_val
                    elif key == 'query': package.extra_metadata['query'] = raw_val
                    else: raise MetadataError(f"METADATA_ERROR: Unknown directive key '{key}'.")

                    if idx < token_count and tokens[idx][0] == 'COMMA': idx += 1
                    continue

                if key in ('flat', 'f'):
                    package.is_flat = True
                else:
                    raise MetadataError(f"METADATA_ERROR: Unrecognized flag '{key}'.")
                idx += 1
                if idx < token_count and tokens[idx][0] == 'COMMA': idx += 1
                continue

            raise MetadataError(f"METADATA_ERROR: Unexpected token '{value}' during directive parsing.")

    @staticmethod
    def _to_int(key: str, value: str) -> int:
        try:
            parsed_value = int(value)
        except ValueError:
            raise MetadataError(f"METADATA_ERROR: Directive '{key}' expects an integer, received '{value}'.")

        if parsed_value < 0:
            raise MetadataError(f"METADATA_ERROR: Directive '{key}' cannot accept a negative value, received '{value}'.")

        return parsed_value

    @staticmethod
    def _parse_logic_clause(content: str) -> Tuple[str, bool]:
        raw_text = content.strip()
        lower_text = raw_text.lower()

        if lower_text.startswith('where'):
            return raw_text[5:].strip(), False
        if lower_text.startswith('!where'):
            return raw_text[6:].strip(), True

        raise MetadataError("METADATA_ERROR: Logic blocks must start with 'where' or '!where'.")
