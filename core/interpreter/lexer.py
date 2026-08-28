from enum import Enum, auto
from dataclasses import dataclass

class TokenType(Enum):
    KEYWORD = auto()
    METADATA = auto()
    BLOCK_START = auto()
    BLOCK_END = auto()
    SEMICOLON = auto()
    STRING = auto()
    RAW_TEXT = auto()

@dataclass
class Token:
    type: TokenType
    value: str
    line: int
    column: int

class LexerError(Exception):
    pass

class Lexer:
    def __init__(self, script_content: str):
        self.text = script_content
        self.current_position = 0
        self.line = 1
        self.column = 1

    def _peek(self, offset: int = 0):
        if self.current_position + offset >= len(self.text):
            return None
        return self.text[self.current_position + offset]

    def _advance(self):
        char = self._peek()
        if char is None:
            raise LexerError(f"LEXER_ERROR: Unexpected end of input at line {self.line}, col {self.column}.")
        
        self.current_position += 1
        if char == '\n':
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def tokenize(self):
        tokens = []
        while self.current_position < len(self.text):
            char = self._peek()
            
            if char.isspace():
                self._advance()
                continue
                
            if char == '/' and self._peek(1) == '/':
                while self._peek() is not None and self._peek() != '\n':
                    self._advance()
                continue
                
            if char == '"':
                tokens.append(self._process_string_literal())
            elif char == '{':
                tokens.append(Token(TokenType.BLOCK_START, self._advance(), self.line, self.column))
            elif char == '}':
                tokens.append(Token(TokenType.BLOCK_END, self._advance(), self.line, self.column))
            elif char == ';':
                tokens.append(Token(TokenType.SEMICOLON, self._advance(), self.line, self.column))
            elif char in '([':
                tokens.append(self._process_metadata_group(char))
            elif char in ')]':
                raise LexerError(f"LEXER_ERROR: Unmatched closing character '{char}' at line {self.line}, col {self.column}.")
            else:
                tokens.append(self._process_raw_identifier())
                
        return tokens

    def _process_string_literal(self):
        start_column, start_line = self.column, self.line
        self._advance()
        content = '"'
        is_closed = False
        
        while self._peek() is not None:
            if self._peek() == '"':
                content += self._advance()
                is_closed = True
                break
            if self._peek() == '\n':
                raise LexerError(f"LEXER_ERROR: Unterminated string starting at line {start_line}, col {start_column}.")
            if self._peek() == '\\' and self._peek(1) is not None:
                content += self._advance()
                content += self._advance()
                continue
            content += self._advance()
            
        if not is_closed:
            raise LexerError(f"LEXER_ERROR: Unterminated string starting at line {start_line}, col {start_column}.")
        return Token(TokenType.STRING, content, start_line, start_column)

    def _process_metadata_group(self, open_char):
        start_column, start_line = self.column, self.line
        close_char = ')' if open_char == '(' else ']'
        content, depth = "", 0
        
        while self.current_position < len(self.text):
            char = self._peek()
            if char == '"':
                string_token = self._process_string_literal()
                content += string_token.value
                continue
            
            char = self._advance()
            content += char
            if char == open_char:
                depth += 1
            elif char == close_char:
                depth -= 1
                if depth == 0:
                    return Token(TokenType.METADATA, content, start_line, start_column)
                    
        raise LexerError(f"LEXER_ERROR: Unclosed group '{open_char}' starting at line {start_line}, col {start_column}.")

    def _process_raw_identifier(self):
        start_column, start_line = self.column, self.line
        content = ""
        reserved_chars = '{};"()[]'
        
        while True:
            char = self._peek()
            if char is None or char.isspace() or char in reserved_chars:
                break
            if char == '/' and self._peek(1) == '/':
                break
            content += self._advance()
            
        if not content:
            raise LexerError(f"LEXER_ERROR: Unexpected character '{self._peek()}' at line {self.line}, col {self.column}.")
        return Token(TokenType.RAW_TEXT, content, start_line, start_column)