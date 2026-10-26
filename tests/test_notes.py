import unittest

from build import split_notes


class NoteSplittingTests(unittest.TestCase):
    def test_independent_terms_keep_their_explanations(self):
        self.assertEqual(
            split_notes('骥：千里马。枥：马槽。烈士：有雄心壮志的人。'),
            ['骥：千里马。', '枥：马槽。', '烈士：有雄心壮志的人。'],
        )

    def test_multiple_sentences_belong_to_one_term(self):
        self.assertEqual(
            split_notes('王：王濛，字仲祖。二人都是清谈名士。林公：支遁。'),
            ['王：王濛，字仲祖。二人都是清谈名士。', '林公：支遁。'],
        )

    def test_punctuation_inside_quotes_is_not_a_boundary(self):
        text = '引文：《论语》载：“子曰：‘学而时习之。说：喜悦。’”说明：补充。'
        self.assertEqual(split_notes(text), [text[:-6], '说明：补充。'])

    def test_parenthetical_colon_stays_inside_explanation(self):
        self.assertEqual(
            split_notes('秩：官俸（存疑：一说二千石）。俸：薪俸。'),
            ['秩：官俸（存疑：一说二千石）。', '俸：薪俸。'],
        )

    def test_citation_and_followup_are_one_note(self):
        text = '事见《论语》：“吾道一以贯之。”曾子曰：“忠恕而已矣。”洪迈的看法是：二者有别。'
        self.assertEqual(split_notes(text), [text])

    def test_term_ending_in_citation_verb_is_still_split(self):
        self.assertEqual(split_notes('葩：花。子云：扬雄。载：装载。'),
                         ['葩：花。', '子云：扬雄。', '载：装载。'])

    def test_quoted_terms_without_colons(self):
        self.assertEqual(split_notes('“致仕”即退休。“易箦”指换席。'),
                         ['“致仕”即退休。', '“易箦”指换席。'])

    def test_compound_quoted_label_and_semicolon(self):
        self.assertEqual(split_notes('释义：说明；“欲饭饭之，欲钱钱之”：给饭给钱。'),
                         ['释义：说明；', '“欲饭饭之，欲钱钱之”：给饭给钱。'])


if __name__ == '__main__':
    unittest.main()
