from generated_script import solution, TreeNode

def test_solution_identical_trees():
    tree1 = TreeNode(1, TreeNode(2), TreeNode(3))
    tree2 = TreeNode(1, TreeNode(2), TreeNode(3))
    assert solution(tree1, tree2) == True

def test_solution_different_trees():
    tree1 = TreeNode(1, TreeNode(2), TreeNode(3))
    tree3 = TreeNode(1, TreeNode(2), TreeNode(4))
    assert solution(tree1, tree3) == False

def test_solution_one_empty_tree():
    tree1 = None
    tree2 = TreeNode(1)
    assert solution(tree1, tree2) == False

def test_solution_both_empty_trees():
    tree1 = None
    tree2 = None
    assert solution(tree1, tree2) == True