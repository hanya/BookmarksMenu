#  Copyright 2012 Tsutomu Uchino
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

def fill_tree(window, root, tree_root_node, broadcast=True):
    """ Fill tree of the window. """
    tree_root_node.set_data(root)
    fill_tree_node(window, tree_root_node, root, broadcast)
    if not broadcast:
        window.tree_get_data_model().structure_changed(
            window.tree_get_root_node())


def fill_tree_node(window, tree_node, container, broadcast=True):
    """ Fill tree node by its child folders. """
    for child in container.get_children():
        if child.is_container():
            tree_child_node = window.tree_create_node(
                                    child.get_name(), True)
            tree_node.append_child(tree_child_node, broadcast)
            tree_child_node.set_data(child)
            fill_tree_node(window, tree_child_node, child, broadcast)


def get_tree_node_expanded_state(window, root_node):
    """ Returns complete expanded state of tree nodes. """
    def check_node(_node_defs, node):
        if window.tree_is_node_expanded(node):
            _node_hierarchi = []
            _node = node.get_parent()
            while _node.get_data():
                if _node:
                    _node_hierarchi.append(_node)
                _node = _node.get_parent()
            ids = [str(_node.get_data().get_id()) 
                        for _node in _node_hierarchi]
            ids.reverse()
            ids.append(str(node.get_data().get_id()))
            _node_defs.append(",".join(ids))
        if node.get_child_count():
            for child in node.get_children():
                check_node(_node_defs, child)
    
    node_state = []
    check_node(node_state, root_node)
    return ";".join(node_state)


def restore_tree_node_expanded_state(window, tree_root, state):
    """ Expand node according to state. """
    if not state:
        return
    states = state.split(";")
    if state and len(states) > 0:
        window.tree_expand_node(tree_root)
    for _node_def in states:
        ids = _node_def.split(",")
        node = tree_root
        # ignore parent
        for id in ids[1:]:
            _id = int(id)
            for child in node.get_children():
                if _id == child.get_data().get_id():
                    node = child
                    break
        if node:
            window.tree_expand_node(node)

