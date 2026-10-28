import unittest

from build import split_pairs


class SentencePairTests(unittest.TestCase):
    def test_explicit_pairs_preserve_sentence_after_leading_comma(self):
        original = '女叹息曰：“事至此，已不能羞。，但渠不嫌寒贱，即遣媒来，病当愈。”'
        translated = '她叹道：“到此地步，已经顾不得害羞。¦只要他不嫌贫贱，遣媒来，病就会好。”'
        pairs = split_pairs(original, translated)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(''.join(o for o, _ in pairs), original)
        self.assertEqual([t for _, t in pairs], translated.split('¦'))

    def test_punctuation_only_fragment_stays_with_previous_sentence(self):
        self.assertEqual(
            split_pairs('甲。）。乙。', '一。¦）。¦二。'),
            [('甲。）。', '一。）。'), ('乙。', '二。')],
        )

    def test_automatic_continuation_keeps_existing_pairing(self):
        self.assertEqual(
            split_pairs('甲。，乙。丙。', '第一。第二。'),
            [('甲。，乙。', '第一。'), ('丙。', '第二。')],
        )
