def get_subtree(tree, children_id):
    # Выделение поддерева в отдельное дерево по индексу вершины
    nodes = [tree]
    while nodes:
        this_token = nodes[0]
        nodes = nodes[1:]
        if this_token.token['id'] == children_id:
            return this_token
        else:
            nodes += this_token.children
    raise IndexError('No children id in the tree')


def get_sentence(tree):
    # Восстановление предложения по дереву
    nodes = [tree]
    words = {}
    while nodes:
        this_token = nodes.pop()
        words[this_token.token['id']] = this_token.token['form']
        nodes += this_token.children
    sorted_words = sorted(words.items())
    return ' '.join([item[1] for item in sorted_words])


def remove_subtree(tree, children_id):
    # Удаление поддерева из дерева по индексу вершины
    nodes = [tree]
    while nodes:
        this_token = nodes[0]
        nodes = nodes[1:]
        these_children = this_token.children
        for i, child in enumerate(these_children):
            if child.token['id'] == children_id:
                del these_children[i]
                this_token.children = these_children
                return
        nodes += this_token.children
    raise IndexError('No children id in the tree')