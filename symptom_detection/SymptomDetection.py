import conllu
import pymorphy2
import re
# import nltk
# import dash_html_components as html

from dash import html
from razdel import sentenize
from pyaspeller import YandexSpeller
from deeppavlov import build_model, configs
from symptom_detection.conllu_tree_utils import get_sentence, get_subtree
from nltk.corpus import stopwords

# nltk.download("stopwords")
russian_stopwords = stopwords.words("russian")
russian_stopwords.extend(['это', 'нею'])

normalizer = pymorphy2.MorphAnalyzer()
speller = YandexSpeller()
syntaxer = build_model(configs.syntax.syntax_ru_syntagrus_bert, download=False)
SYMPTOM_PATH = r'data\symptom_glossary.txt'

with open(SYMPTOM_PATH) as f:
    SYMPTOM_WORDS = f.read().split('\n')

negation_words = [
    'не',
    'нет',
    'отрицать',
    'отсутствовать',
    'без',
    'избегать',
    'отказаться',
    'отсутствие',
]

color_dict = {
    'black': '#000000',
    'red': '#E74C3C',
    'blue': '#2980B9',
}


def traverse_up_and_check_negations(parents, check_id):
    this_id = check_id
    while this_id in parents:

        if parents[this_id][2] in negation_words:
            return True

        # Check 'не'
        for child_id, (child_word, parent_id, parent_word) in parents.items():
            if parent_id == parents[this_id][1] and child_word in ['не', 'без']:
                return True

        this_id = parents[this_id][1]

    return False


def check_negations(tree, check_id):
    nodes = [tree]
    parents = {}
    while nodes:
        this_token = nodes[0]
        nodes = nodes[1:]
        this_word = this_token.token['form']
        this_id = this_token.token['id']
        norm_word = normalizer.normal_forms(this_word.strip(' ,.:()-?\\/'))[0]
        if this_id == check_id:
            return traverse_up_and_check_negations(parents, check_id)
        for next_token in this_token.children:
            nodes.append(next_token)
            next_norm_word = next_token.token['form']
            parents[next_token.token['id']] = (next_norm_word, this_id, norm_word)


def find_symp_words_and_subtrees(tree, full_subtree=True):
    result = []
    nodes = [tree]
    while nodes:
        this_token = nodes[0]
        nodes = nodes[1:]
        this_word = this_token.token['form']
        this_id = this_token.token['id']
        norm_word = normalizer.normal_forms(this_word.strip(' ,.:()-?\\/'))[0]
        if norm_word in SYMPTOM_WORDS:
            negation_status = check_negations(tree, this_id)
            if full_subtree:
                result.append((norm_word, get_sentence(get_subtree(tree, this_id)), negation_status))
            else:
                descriptions = []
                for cn in this_token.children:
                    descriptions.append(get_sentence(get_subtree(tree, cn.token['id'])))
                result.append([norm_word, descriptions, negation_status])
        nodes += this_token.children
    return result


def tokenize_for_sentences(text):
    res = []
    for sent_token in sentenize(text):
        res.append(sent_token.text + ' ')
    return res


def curtail_to_comma(detections, sign=','):
    curtailed_detections = []
    for main_word, det, neg_status in detections:
        if sign in det:
            cur_det = det.split(sign)[0].strip()
            if len(cur_det) == 0:
                cur_det = det.split(sign)[1].strip()
            det = cur_det
        curtailed_detections.append((main_word, det, neg_status))
    return curtailed_detections


def remove_repeats(detections):
    these_dets = sorted(detections, key=lambda x: len(x[1]))
    index_to_remove = []
    for i, det in enumerate(these_dets):
        for j, bigger_det in enumerate(these_dets[i + 1:], i + 1):
            if i in index_to_remove:
                break
            if det[1] in bigger_det[1]:
                index_to_remove.append(i)
    for indexx in index_to_remove[::-1]:
        del these_dets[indexx]
    return these_dets


def remove_long_details(detections, signs_to_remove=(',')):
    short_detections = []
    for det in detections:
        main_word, details, neg_status = det
        short_details = []
        for detail in details:
            for sign in signs_to_remove:
                if sign in detail:
                    break
            else:
                short_details.append(detail)
        short_detections.append([main_word, short_details, neg_status])
    return short_detections


def sort_detections(dets, sent):
    dets_filter_none = [det for det in dets if sent.find(det[1]) >= 0]
    return sorted(
        dets_filter_none,
        key=lambda x: sent.find(x[1])
    )


def split_sent_by_dets(dets, sent):
    aligned_dets = []
    for det in dets:
        if det[1] not in sent:
            aligned_dets.extend(align_det_for_sent(det, sent))
        else:
            aligned_dets.append(det)
    dets = sort_detections(aligned_dets, sent)
    # print([sent.find(x[1]) for x in dets])
    parts = []
    for _, det, neg_status in dets:
        sent_part_before = sent.split(det)[0]
        if len(sent_part_before) > 0:
            parts.append((None, sent_part_before, None))
        parts.append((_, det, neg_status))
        sent = ' '.join(sent.split(det)[1:])
    if len(sent) > 0:
        parts.append((None, sent, None))
    return parts


def align_det_for_sent(detection, sent):
    main_word, phrase, neg_status = detection
    words = phrase.split(' ')
    start_loc = 0
    word_locs = []
    for word in words:
        start_word_loc = start_loc + sent[start_loc:].find(word)
        finish_word_loc = start_word_loc + len(word)
        word_locs.append((start_word_loc, finish_word_loc))
        start_loc = finish_word_loc
    #     print(word_locs)

    prev_loc = word_locs[0]
    total_locs = [[prev_loc[0], None]]
    skip_locs = []
    for this_loc in word_locs[1:]:
        start, finish = this_loc
        prev_start, prev_finish = prev_loc
        if prev_finish + 1 != start and prev_finish != start:
            total_locs[-1][-1] = prev_finish
            total_locs.append([start, None])
            skip_locs.append([prev_finish, start])
        prev_loc = this_loc
    total_locs[-1][-1] = finish
    #     print(total_locs)
    #     print(skip_locs)

    #     for locs in total_locs:
    #         print(sent[slice(*locs)])

    new_detections = []
    for locs in total_locs:
        new_phrase = sent[slice(*locs)]
        new_detections.append([main_word, new_phrase, neg_status])

    return new_detections


def tune_details(detection):
    nomn_case = 'nomn'
    adjf_pos = 'ADJF'
    main_word, details, neg_status = detection
    main_word_morph = normalizer.parse(main_word)[0]
    states = {main_word_morph.tag.gender, main_word_morph.tag.number, nomn_case}
    tuned_detection = [main_word, [], neg_status]
    for det in details:
        words = det.split(' ')
        if len(words) == 1:
            if det.lower() in russian_stopwords:
                continue
            det_morph = normalizer.parse(det)[0]
            det_pos = det_morph.tag.POS
            if det_pos is None:
                continue
            if det_pos in (adjf_pos):
                tuned_det = det_morph.inflect(states).word
                tuned_detection[1].append(tuned_det)
                continue
        tuned_detection[1].append(det)
    return tuned_detection


def tune_total_detections(detections):
    tuned_detections = []
    for sent in detections:
        sent_dets = list(filter(lambda res: res is not None, [tune_details(det) for det in sent]))
        tuned_detections.append(sent_dets)
    return tuned_detections


def remove_html_tags(text):
    tag_pattern = re.compile('<[^>]*>')
    tag_replace = '. '
    new_line_pattern = re.compile(' *\n+')
    new_line_replace = tag_replace
    multiple_stops_pattern = re.compile('(\. *)+')
    multiple_stops_replace = '. '
    text = re.sub(tag_pattern, tag_replace, text)
    text = re.sub(new_line_pattern, new_line_replace, text)
    text = re.sub(multiple_stops_pattern, multiple_stops_replace, text)
    return text


def detect_symptoms(text, return_text_mode='span'):
    """
    Detect and extract symptoms in a free-form text.
    return_mode: 'span' - return text with span for dash visualization
    'ansi' - return text with ANSI terminal pattern for jupyter visualization
    """
    text_without_html = remove_html_tags(text)
    sentences = tokenize_for_sentences(text_without_html)
    detected_results = []
    full_detections = []
    ansi_text = ''
    span_obj = []

    for sent in sentences:
        fixed_sent = speller.spelled(sent)
        this_parsed = syntaxer([fixed_sent])[0]
        this_tree = conllu.parse(this_parsed)
        if len(this_tree) > 1:
            print("MORE THAN ONE TREE!")
        this_tree = this_tree[0].to_tree()

        full_detection = find_symp_words_and_subtrees(this_tree)
        short_full_detection = curtail_to_comma(full_detection)
        clean_short_full_detection = remove_repeats(short_full_detection)
        detailed_detection = find_symp_words_and_subtrees(this_tree, full_subtree=False)
        short_detailed_detection = remove_long_details(detailed_detection)
        clean_short_detailed_detection = remove_repeats(short_detailed_detection)

        if return_text_mode == 'ansi':
            if len(clean_short_full_detection):
                new_sent = fixed_sent
                for _, detected, negation_status in clean_short_full_detection:
                    if negation_status:
                        new_sent = new_sent.replace(detected, f"\x1b[34m{detected}\x1b[0m")
                    else:
                        new_sent = new_sent.replace(detected, f"\x1b[31m{detected}\x1b[0m")
                ansi_text += new_sent
            else:
                ansi_text += fixed_sent

        if return_text_mode == 'span':
            if len(clean_short_full_detection):
                new_span = []
                det_parts = split_sent_by_dets(clean_short_full_detection, fixed_sent)
                for _, part, negation_status in det_parts:
                    if negation_status is None:
                        new_span.append(
                            html.Span(part, style={'color': color_dict['black']})
                        )
                    elif negation_status:
                        new_span.append(
                            html.Span(part, style={'color': color_dict['blue']})
                        )
                    else:
                        new_span.append(
                            html.Span(part, style={'color': color_dict['red']})
                        )
                span_obj.extend(new_span)
            else:
                span_obj.append(
                    html.Span(fixed_sent, style={'color': color_dict['black']})
                )

        detected_results.append(clean_short_detailed_detection)
        full_detections.append(full_detection)

    if return_text_mode == 'span':
        return tune_total_detections(detected_results), span_obj
    if return_text_mode == 'ansi':
        return tune_total_detections(detected_results), ansi_text


# [[['боль', ['головная', 'в теменно-затылочной области'], False]],
#  [['одышка', [], False]],
#  [['боль', [], False]],
#  [['стенокардия', ['нестабильная'], False]],
#  [],]

# html.Div([
#         html.P('Dash converts Python classes into HTML'),
#         html.P("This conversion happens behind the scenes by Dash's JavaScript front-end")
#     ])


def detections_to_li_html(detections, neg_status=False):
    html_elements = []
    # print(detections)
    for sent_dets in detections:
        for det in sent_dets:
            symptom, details, this_neg_stat = det
            if this_neg_stat == neg_status:
                symptom_text = f'- {symptom}'
                if len(details) == 0:
                    html_elements.append(html.P(symptom_text))
                    continue
                symptom_text += ':'
                html_elements.append(html.P(symptom_text))
                html_elements.extend([html.Li(d) for d in details])
    return html.Div(html_elements)


if __name__ == '__main__':
    # TODO: починить проблему с запятыми
    # Кашель, чихание, ухудшение самочувствия не беспокоят. Головокружения в течение недели.
    pass

