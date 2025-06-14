def test_indentation():
    with open('../controllers/prediction.py', 'r') as file:
        lines = file.readlines()
        assert all(line.startswith(' ') or line.startswith('\t') for line in lines), "Indentation error found in prediction.py"

[pytest]
testpaths = tests
