"""Simple markdown parser for note editor."""
import re
from PyQt6.QtGui import QTextCursor, QTextBlockFormat, QTextCharFormat, QFont, QTextListFormat


class MarkdownParser:
    """Convert markdown syntax to rich text formatting."""
    
    @staticmethod
    def process_line(cursor: QTextCursor, line: str) -> bool:
        """
        Process a line for markdown syntax and apply formatting.
        Returns True if the line was converted, False otherwise.
        """
        # Check for horizontal rule (---, ___, ***)
        if re.match(r'^(-{3,}|_{3,}|\*{3,})$', line.strip()):
            # Select and remove the current line
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            # Insert HR
            cursor.insertHtml('<hr>')
            # Insert normal paragraph below
            cursor.insertBlock()
            # Reset to normal format
            block_format = QTextBlockFormat()
            cursor.setBlockFormat(block_format)
            char_format = QTextCharFormat()
            cursor.setCharFormat(char_format)
            return True
        
        # Check for headers (# Header, ## Header, etc.)
        header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if header_match:
            level = len(header_match.group(1))
            text = header_match.group(2)
            # Select and remove the current line
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            
            # Set header format
            if level == 1:
                cursor.insertHtml(f'<h1>{text}</h1>')
                block_format = QTextBlockFormat()
                cursor.setBlockFormat(block_format)
                char_format = QTextCharFormat()
                cursor.setCharFormat(char_format)
            elif level == 2:
                cursor.insertHtml(f'<h2>{text}</h2>')
                block_format = QTextBlockFormat()
                cursor.setBlockFormat(block_format)
                char_format = QTextCharFormat()
                cursor.setCharFormat(char_format)
            elif level == 3:
                cursor.insertHtml(f'<h3>{text}</h3>')
                block_format = QTextBlockFormat()
                cursor.setBlockFormat(block_format)
                char_format = QTextCharFormat()
                cursor.setCharFormat(char_format)
            elif level == 4:
                cursor.insertHtml(f'<h4>{text}</h4>')
                block_format = QTextBlockFormat()
                cursor.setBlockFormat(block_format)
                char_format = QTextCharFormat()
                cursor.setCharFormat(char_format)
            elif level == 5:
                cursor.insertHtml(f'<h5>{text}</h5>')
                block_format = QTextBlockFormat()
                cursor.setBlockFormat(block_format)
                char_format = QTextCharFormat()
                cursor.setCharFormat(char_format)
            else:
                cursor.insertHtml(f'<h6>{text}</h6>')
                block_format = QTextBlockFormat()
                cursor.setBlockFormat(block_format)
                char_format = QTextCharFormat()
                cursor.setCharFormat(char_format)
            
            # Insert normal paragraph below
            cursor.insertBlock()
            return True
        
        # Check for bullet list (- item, * item, + item)
        if re.match(r'^[-*+]\s+.+$', line):
            text = re.sub(r'^[-*+]\s+', '', line)
            # Select and remove the current line
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            # Create list format closer to left
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.Style.ListDisc)
            list_format.setIndent(1)  # Need at least 1 for list to work
            cursor.insertList(list_format)
            cursor.insertText(text)
            # Reset format after list item
            char_format = QTextCharFormat()
            cursor.setCharFormat(char_format)
            return True
        
        # Check for numbered list (1. item, 2. item)
        if re.match(r'^\d+\.\s+.+$', line):
            text = re.sub(r'^\d+\.\s+', '', line)
            # Select and remove the current line
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            # Create list format closer to left
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.Style.ListDecimal)
            list_format.setIndent(1)  # Need at least 1 for list to work
            cursor.insertList(list_format)
            cursor.insertText(text)
            # Reset format after list item
            char_format = QTextCharFormat()
            cursor.setCharFormat(char_format)
            return True
        
        # Check for blockquote (> text)
        if line.startswith('> '):
            text = line[2:]
            # Select and remove the current line
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.insertHtml(f'<blockquote style="border-left: 4px solid #4CAF50; padding-left: 15px; margin-left: 5px; background-color: rgba(76, 175, 80, 0.1); font-style: italic; color: #888;">{text}</blockquote>')
            # Insert normal paragraph below
            cursor.insertBlock()
            # Reset to normal format
            block_format = QTextBlockFormat()
            cursor.setBlockFormat(block_format)
            char_format = QTextCharFormat()
            cursor.setCharFormat(char_format)
            return True
        
        return False
    
    @staticmethod
    def convert_inline_markdown(text: str) -> str:
        """Convert inline markdown syntax (bold, italic, code) to HTML."""
        # Bold (**text** or __text__)
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
        
        # Italic (*text* or _text_)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        text = re.sub(r'_(.+?)_', r'<em>\1</em>', text)
        
        # Inline code (`code`)
        text = re.sub(r'`(.+?)`', r'<code style="background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px;">\1</code>', text)
        
        # Strikethrough (~~text~~)
        text = re.sub(r'~~(.+?)~~', r'<del>\1</del>', text)
        
        return text

