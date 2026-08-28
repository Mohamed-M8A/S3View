from core.loader import PluginLoader
from core.models.structures import CommandModel
from core.filter import FilterEngine
from .lexer import Lexer, TokenType, LexerError
from .parsers import Metadata, MetadataError, MetadataPackage
from .parsers import ActionParsers as Actions

class BuildError(Exception):
    pass

class Builder:
    @staticmethod
    def build(script_content: str):
        try:
            lexer = Lexer(script_content)
            tokens = lexer.tokenize()
        except LexerError as exc:
            raise BuildError(str(exc))

        loader = PluginLoader()
        loader.discover_plugins()
        pipeline = []
        index = 0
        token_count = len(tokens)

        while index < token_count:
            token = tokens[index]
            if token.type != TokenType.RAW_TEXT:
                raise BuildError(f"SYNTAX_ERROR: Unexpected token '{token.value}' at line {token.line}.")

            keyword = token.value
            keyword_line = token.line
            shared_metadata_raw = ""
            index += 1

            while index < token_count and tokens[index].type == TokenType.METADATA:
                shared_metadata_raw += tokens[index].value
                index += 1

            if index < token_count and tokens[index].type == TokenType.BLOCK_START:
                index += 1
                block_orders, index = Builder._collect_block_scope(tokens, index, keyword)
                Builder._compile_to_pipeline(keyword, shared_metadata_raw, block_orders, loader, pipeline, keyword_line)
            else:
                inline_order, index = Builder._collect_inline_order(tokens, index, keyword)
                Builder._compile_to_pipeline(keyword, shared_metadata_raw, [inline_order], loader, pipeline, keyword_line)

        return pipeline

    @staticmethod
    def _collect_inline_order(tokens, index, keyword):
        token_count = len(tokens)
        order_text_parts = []
        specific_metadata = ""

        while index < token_count and tokens[index].type != TokenType.SEMICOLON:
            if tokens[index].type == TokenType.METADATA:
                specific_metadata += tokens[index].value
            elif tokens[index].type in (TokenType.RAW_TEXT, TokenType.STRING):
                order_text_parts.append(tokens[index].value)
            else:
                raise BuildError(f"SYNTAX_ERROR: Unexpected token in '{keyword}' at line {tokens[index].line}.")
            index += 1

        if index >= token_count:
            raise BuildError(f"SYNTAX_ERROR: Command '{keyword}' is missing a terminating semicolon ';'.")

        index += 1
        return (" ".join(order_text_parts).strip(), specific_metadata), index

    @staticmethod
    def _collect_block_scope(tokens, index, keyword):
        token_count = len(tokens)
        orders = []
        order_text_parts = []
        specific_metadata = ""

        while index < token_count and tokens[index].type != TokenType.BLOCK_END:
            if tokens[index].type == TokenType.SEMICOLON:
                orders.append((" ".join(order_text_parts).strip(), specific_metadata))
                order_text_parts = []
                specific_metadata = ""
            elif tokens[index].type == TokenType.METADATA:
                specific_metadata += tokens[index].value
            elif tokens[index].type in (TokenType.RAW_TEXT, TokenType.STRING):
                order_text_parts.append(tokens[index].value)
            else:
                raise BuildError(f"SYNTAX_ERROR: Invalid token inside block '{keyword}' at line {tokens[index].line}.")
            index += 1

        if index >= token_count:
            raise BuildError(f"SYNTAX_ERROR: Block for '{keyword}' is missing a closing brace '}}'.")

        if order_text_parts or specific_metadata:
            orders.append((" ".join(order_text_parts).strip(), specific_metadata))

        index += 1
        if not orders:
            raise BuildError(f"BUILD_ERROR: Block for '{keyword}' cannot be empty.")

        return orders, index

    @staticmethod
    def _compile_to_pipeline(keyword, shared_meta_raw, orders, loader, pipeline, keyword_line=None):
        plugin_info = loader.get_plugin_and_flags_by_keyword(keyword)
        if not plugin_info:
            raise BuildError(f"BUILD_ERROR: Unknown command keyword '{keyword}'.")

        line_suffix = f" at line {keyword_line}" if keyword_line is not None else ""

        try:
            shared_pkg = Metadata.extract(shared_meta_raw) if shared_meta_raw else MetadataPackage()
        except MetadataError as exc:
            raise BuildError(f"METADATA_ERROR in '{keyword}'{line_suffix}: {exc}")

        method_name = plugin_info.get("parser_method")

        if not method_name or not hasattr(Actions, method_name):
            raise BuildError(f"BUILD_ERROR: No parser method defined for keyword '{keyword}'.")

        parser_function = getattr(Actions, method_name)

        for order_text, order_meta_raw in orders:
            if not order_text:
                raise BuildError(f"BUILD_ERROR: Command '{keyword}'{line_suffix} contains an empty order.")

            try:
                order_pkg = Metadata.extract(order_meta_raw) if order_meta_raw else shared_pkg
            except MetadataError as exc:
                raise BuildError(f"METADATA_ERROR in '{keyword}'{line_suffix}: {exc}")

            merged_metadata = Builder._merge_metadata_packages(plugin_info, shared_pkg, order_pkg)
            command_object = parser_function(order_text, merged_metadata)

            if isinstance(command_object, dict) and "error" in command_object:
                raise BuildError(f"PARSER_ERROR in '{keyword}': {command_object['error']}")

            if not isinstance(command_object, CommandModel):
                raise BuildError(f"BUILD_ERROR: Parser for '{keyword}' returned an invalid data structure.")

            command_object.trigger_mode = keyword
            command_object.logic_inversion = order_pkg.logic_inversion if order_pkg.logic is not None else shared_pkg.logic_inversion
            command_object.compiled_logic = FilterEngine.compile_logic(command_object.logic)

            if plugin_info.get("flags"):
                command_object.extra_metadata.update(plugin_info["flags"])

            pipeline.append({"action": plugin_info["plugin"].action_name, "data": command_object})

    @staticmethod
    def _merge_metadata_packages(plugin_info, shared: MetadataPackage, order: MetadataPackage):
        return {
            "action": plugin_info["plugin"].action_name,
            "exclusions": order.exclusions if order.exclusions else shared.exclusions,
            "logic": order.logic if order.logic is not None else shared.logic,
            "limit": order.limit if order.limit is not None else shared.limit,
            "depth": order.depth if order.depth is not None else shared.depth,
            "tier": order.tier if order.tier is not None else shared.tier,
            "expires": order.expires if order.expires is not None else shared.expires,
            "level": order.level if order.level is not None else shared.level,
            "chunk_size": order.chunk_size if order.chunk_size is not None else shared.chunk_size,
            "is_flat": order.is_flat or shared.is_flat,
            "workers": order.workers if order.workers is not None else shared.workers,
            "task_timeout": order.task_timeout if order.task_timeout is not None else shared.task_timeout,
            "extra_metadata": {**shared.extra_metadata, **order.extra_metadata},
        }