import os
import re

import spacy
from spacy.language import Language

from typing import List, Dict, Any


@Language.component("unknown_token_fixer")
def unknown_token_fixer(doc):
    for token in doc:
        if token.pos_ in ("PUNCT", "SPACE"):
            continue

        if token.is_punct:
            token.pos_ = "PUNCT"
            continue

        has_letter = any(c.isalpha() for c in token.text)
        has_digit = any(c.isdigit() for c in token.text)

        if not has_letter and not has_digit:
            token.pos_ = "SYM"

        elif has_digit and not has_letter and token.pos_ == "NOUN":
            token.pos_ = "NUM"

    return doc


class LinguisticProcessor:
    def __init__(self):
        self._nlp = None
        self.allowed_morph_keys = {
            'case', 'gender', 'number', 'animacy',
            'verbform', 'mood', 'tense', 'aspect', 'person', 'voice',
            'degree', 'prontype', 'numtype', 'poss', 'reflex', 'polarity'
        }

    @property
    def nlp(self):
        if self._nlp is None:
            model_name = os.environ.get('SPACY_MODEL', 'uk_core_news_lg')
            self._nlp = spacy.load(model_name, exclude=["parser", "ner"])
            self._nlp.add_pipe("unknown_token_fixer", after="morphologizer")

            if "sentencizer" not in self._nlp.pipe_names:
                self._nlp.add_pipe("sentencizer")

            ruler = self._nlp.get_pipe("attribute_ruler")
            ruler.add(patterns=[[{"IS_DIGIT": True}]], attrs={"POS": "NUM"})
        return self._nlp

    def _chunk_text(self, text: str) -> List[str]:
        healed_text = re.sub(r'\n\s*([а-яіїєґa-z])', r' \1', text) # Merge mid-sentence line breaks followed by a lowercase character
        return [p.strip() for p in healed_text.split('\n') if p.strip()]

    def process_input_content(self, input_content: str, batch_size: int = 64, chunk_size: int = 200) -> List[Dict[str, Any]]:
        if not input_content or not input_content.strip():
            return []

        chunks = self._chunk_text(input_content)
        processed_data = []

        for i in range(0, len(chunks), chunk_size):
            batch = chunks[i:i + chunk_size]
            for doc in self.nlp.pipe(batch, batch_size=batch_size):
                for sent in doc.sents:
                    filtered_tokens = []

                    for token in sent:
                        if token.pos_ in ("PUNCT", "SPACE"):
                            continue

                        raw_morph = token.morph.to_dict()
                        filtered_morph = {
                            k.lower(): v.lower()
                            for k, v in raw_morph.items()
                            if k.lower() in self.allowed_morph_keys
                        }

                        filtered_tokens.append({
                            "form": token.text.lower(),
                            "lemma": token.lemma_.lower(),
                            "pos": token.pos_,
                            "morph": filtered_morph
                        })

                    if filtered_tokens:
                        processed_data.append({
                            "original_sentence_text": sent.text.strip(),
                            "tokens": filtered_tokens
                        })

        return processed_data

lingustic_processor_instance = LinguisticProcessor()
