import re
from typing import List, Dict


class TextProcessor:
    def __init__(self):
        self.pos_mapping = {
            'іменник': 'NOUN',
            'власна назва': 'PROPN',
            'прикметник': 'ADJ',
            'дієслово': 'VERB',
            'дієприслівник': 'VERB',
            'допоміжне дієслово': 'AUX',
            'прислівник': 'ADV',
            'займенник': 'PRON',
            'детермінатив': 'DET',
            'займенникові слова': 'DET',
            'числівник': 'NUM',
            'прийменник': 'ADP',
            'адпозиція': 'ADP',
            'сурядний сполучник': 'CCONJ',
            'підрядний сполучник': 'SCONJ',
            'частка': 'PART',
            'вигук': 'INTJ',
            'пунктуація': 'PUNCT',
            'символ': 'SYM',
            'інше': 'X'
        }


    def parse_cql(self, query: str) -> List[Dict]:
        tokens = []
        parts = re.findall(r'(\[.*?\]|\{.*?\}|".*?"|<\d+>)', query)

        for part in parts:
            rule = {}

            if part.startswith('['):
                val = part.strip('[]').lower()
                rule['pos'] = self.pos_mapping.get(val, val.upper())
            elif part.startswith('{'):
                rule['lemma'] = part.strip('{}').lower()
            elif part.startswith('"'):
                rule['form'] = part.strip('"').lower()
            elif part.startswith('<'):
                rule['distance'] = int(part.strip('<>'))

            if rule:
                tokens.append(rule)

        return tokens


    def build_kwic(self, original_sentence_text, left_context_size, right_context_size, query_rules, es_tokens):
        es_tokens = [t.to_dict() if hasattr(t, 'to_dict') else dict(t) for t in es_tokens]

        coords = []
        current_idx = 0

        safe_text = original_sentence_text.lower().replace("'", "ʼ").replace("’", "ʼ")

        for token_dict in es_tokens:
            form = str(token_dict.get('form', ''))
            if not form:
                coords.append((current_idx, current_idx))
                continue

            safe_form = form.lower().replace("'", "ʼ").replace("’", "ʼ")
            start_char = safe_text.find(safe_form, current_idx)

            if start_char == -1:
                start_char = current_idx

            end_char = start_char + len(form)
            coords.append((start_char, end_char))
            current_idx = end_char

        def match_at(t_idx, r_idx):
            if r_idx == len(query_rules):
                return t_idx - 1
            if t_idx >= len(es_tokens):
                return None

            rule = query_rules[r_idx]

            if 'distance' in rule:
                if r_idx + 1 >= len(query_rules):
                    return None
                max_dist = rule['distance']
                next_rule = query_rules[r_idx + 1]

                for skip in range(max_dist + 1):
                    target_t = t_idx + skip
                    if target_t < len(es_tokens):
                        word_data = es_tokens[target_t]
                        if all(str(word_data.get(k, '')).lower() == str(v).lower() for k, v in next_rule.items()):
                            res = match_at(target_t + 1, r_idx + 2)
                            if res is not None:
                                return res
                return None
            else:
                word_data = es_tokens[t_idx]
                if all(str(word_data.get(k, '')).lower() == str(v).lower() for k, v in rule.items()):
                    return match_at(t_idx + 1, r_idx + 1)
                return None

        ranges_to_mark = []
        for i in range(len(es_tokens)):
            end_t_idx = match_at(i, 0)
            if end_t_idx is not None:
                ranges_to_mark.append((i, end_t_idx))

        kwic_variations = []
        for m_start, m_end in ranges_to_mark:
            char_start = coords[m_start][0]
            char_end = coords[m_end][1]

            if left_context_size is None:
                left_str = original_sentence_text[:char_start]
                add_l_ellipsis = False
            else:
                l_idx = m_start - left_context_size
                if l_idx <= 0:
                    left_str = original_sentence_text[:char_start]
                    add_l_ellipsis = False
                else:
                    left_str = original_sentence_text[coords[l_idx][0]:char_start]
                    add_l_ellipsis = True

            if right_context_size is None:
                right_str = original_sentence_text[char_end:]
                add_r_ellipsis = False
            else:
                target_r_idx = m_end + right_context_size
                if target_r_idx >= len(coords) - 1:
                    right_str = original_sentence_text[char_end:]
                    add_r_ellipsis = False
                else:
                    right_str = original_sentence_text[char_end:coords[target_r_idx][1]]
                    add_r_ellipsis = True

            kwic_variations.append({
                'left_context': ("..." if add_l_ellipsis else "") + left_str.lstrip(),
                'searched_sentence': original_sentence_text[char_start:char_end],
                'right_context': right_str.rstrip() + ("..." if add_r_ellipsis else "")
            })

        return kwic_variations

text_processor_instance = TextProcessor()
