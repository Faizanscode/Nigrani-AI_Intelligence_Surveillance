import re

class PlateValidator:
    """
    Validates common Indian vehicle license plate formats.
    e.g. MP04TB1506, MH12DE1234, DL01CA1234, MP04CC1776
    """
    def __init__(self):
        # Two letters, 1-2 digits, 1-3 letters, 3-4 digits
        self.standard_pattern = re.compile(r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{3,4}$')
        # Defense / BH series plates
        self.defense_pattern = re.compile(r'^\d{2}[A-Z\u2191][\dA-Z]{5,10}$')
        self.bh_pattern = re.compile(r'^\d{2}BH\d{4}[A-Z]{1,2}$')

    def normalize(self, text: str) -> str:
        """
        Convert to uppercase, remove non-alphanumerics, and apply OCR error correction.
        """
        text = text.upper()
        text = re.sub(r'[^A-Z0-9]', '', text)

        # Smart character correction for 9 or 10 character Indian plates
        # Format: LL DD LL DDDD (e.g. MP04TB1506)
        if len(text) == 10:
            char_to_num = {'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'B': '8', 'S': '5'}
            num_to_char = {'0': 'O', '1': 'I', '2': 'Z', '8': 'B', '5': 'S'}

            chars = list(text)
            # Pos 0, 1: Letters (State)
            for i in [0, 1]:
                if chars[i] in num_to_char:
                    chars[i] = num_to_char[chars[i]]
            # Pos 2, 3: Digits (RTO)
            for i in [2, 3]:
                if chars[i] in char_to_num:
                    chars[i] = char_to_num[chars[i]]
            # Pos 4, 5: Letters (Series)
            for i in [4, 5]:
                if chars[i] in num_to_char:
                    chars[i] = num_to_char[chars[i]]
            # Pos 6, 7, 8, 9: Digits (Number)
            for i in [6, 7, 8, 9]:
                if chars[i] in char_to_num:
                    chars[i] = char_to_num[chars[i]]
            text = "".join(chars)

        return text

    def validate(self, normalized_text: str) -> str:
        """
        Returns 'VALID', 'INVALID', or 'UNKNOWN'
        """
        if len(normalized_text) < 4:
            return 'INVALID'

        if self.standard_pattern.match(normalized_text):
            return 'VALID'

        if self.bh_pattern.match(normalized_text):
            return 'VALID'

        if self.defense_pattern.match(normalized_text):
            return 'VALID'

        # If it doesn't match standard patterns but has a typical plate length
        if 8 <= len(normalized_text) <= 11:
            return 'UNKNOWN'

        return 'INVALID'

