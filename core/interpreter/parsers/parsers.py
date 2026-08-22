from core.paths import Paths
from core.models.structures import CommandModel, PathModel


class ActionParsers:

    @staticmethod
    def _is_wrapped_in_quotes(text):
        target = (text or "").strip()
        return len(target) >= 2 and target.startswith('"') and target.endswith('"')


    @staticmethod
    def _extract_validated_path(text):
        if not ActionParsers._is_wrapped_in_quotes(text):
            return None

        return Paths.analyze(text)


    @staticmethod
    def _split_by_keyword(text, keyword):
        length = len(text)
        keyword_length = len(keyword)
        index = 0
        is_inside_quotes = False

        while index < length:
            char = text[index]

            if char == '"':
                if index > 0 and text[index - 1] == '\\':
                    index += 1
                    continue
                is_inside_quotes = not is_inside_quotes
                index += 1
                continue

            if not is_inside_quotes and text[index:index + keyword_length] == keyword:
                boundary_before = (index == 0 or text[index - 1].isspace())
                after_index = index + keyword_length
                boundary_after = (after_index >= length or text[after_index].isspace())

                if boundary_before and boundary_after:
                    return text[:index].strip(), text[after_index:].strip()

            index += 1

        return None


    @staticmethod
    def _apply_mirror_calculation(source: PathModel, destination: PathModel):
        source_clean = source.payload.replace("\\", "/").rstrip("/")

        if not source_clean:
            return destination

        path_segments = source_clean.split("/")
        trailing_segment = path_segments[-1]

        destination_clean = destination.payload.replace("\\", "/").rstrip("/")

        if not destination_clean:
            destination.payload = trailing_segment
        else:
            destination.payload = f"{destination_clean}/{trailing_segment}"

        return destination


    @staticmethod
    def _build_command_model(metadata, source_path=None, destination_path=None, is_mirror=False):
        return CommandModel(
            action=metadata.get("action", "process"),
            src=source_path,
            dst=destination_path,
            is_mirror=is_mirror,
            logic=metadata.get("logic"),
            limit=metadata.get("limit"),
            depth=metadata.get("depth"),
            tier=metadata.get("tier"),
            expires=metadata.get("expires"),
            level=metadata.get("level"),
            chunk_size=metadata.get("chunk_size"),
            exclusions=metadata.get("exclusions", []),
            is_flat=metadata.get("is_flat", False),
            workers=metadata.get("workers"),
            task_timeout=metadata.get("task_timeout")
        )


    @staticmethod
    def parse_nullary(command_text, metadata):
        return ActionParsers._build_command_model(metadata)


    @staticmethod
    def parse_unary(command_text, metadata):
        source = ActionParsers._extract_validated_path(command_text)

        if not source:
            return {"error": f"SYNTAX_ERROR: Path must be wrapped in double quotes -> {command_text}"}

        return ActionParsers._build_command_model(metadata, source)


    @staticmethod
    def parse_binary(command_text, metadata):
        parts = ActionParsers._split_by_keyword(command_text, "to")

        if not parts:
            return {"error": "SYNTAX_ERROR: Binary commands require the 'to' separator."}

        source = ActionParsers._extract_validated_path(parts[0])
        destination = ActionParsers._extract_validated_path(parts[1])

        if not source or not destination:
            return {"error": "SYNTAX_ERROR: Both source and destination paths must be quoted."}

        return ActionParsers._build_command_model(metadata, source, destination)


    @staticmethod
    def parse_reflective(command_text, metadata):
        mirror_parts = ActionParsers._split_by_keyword(command_text, "*to")
        is_mirror_mode = (mirror_parts is not None)

        parts = mirror_parts if is_mirror_mode else ActionParsers._split_by_keyword(command_text, "to")

        if not parts:
            return {"error": "SYNTAX_ERROR: Required separator ('to' or '*to') not found."}

        source = ActionParsers._extract_validated_path(parts[0])
        raw_destination = ActionParsers._extract_validated_path(parts[1])

        if not source or not raw_destination:
            return {"error": "SYNTAX_ERROR: Both paths must be double-quoted."}

        if is_mirror_mode:
            if source.is_cloud != raw_destination.is_cloud:
                return {"error": "SECURITY_ERROR: Mirroring (*to) is only permitted for same-environment transfers (Cloud-to-Cloud or Local-to-Local)."}

            destination = ActionParsers._apply_mirror_calculation(source, raw_destination)
        else:
            destination = raw_destination

        return ActionParsers._build_command_model(metadata, source, destination, is_mirror=is_mirror_mode)


    @staticmethod
    def parse_flexible(command_text, metadata):
        if ActionParsers._split_by_keyword(command_text, "*to") or ActionParsers._split_by_keyword(command_text, "to"):
            return ActionParsers.parse_reflective(command_text, metadata)

        return ActionParsers.parse_unary(command_text, metadata)