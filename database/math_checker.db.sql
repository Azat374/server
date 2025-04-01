INSERT INTO tasks (title, expression, limitVar, expected_value)
VALUES
  (
    '8.1. lim ((2x+3)/(5x+7))^(x+1)',
    '((2*x + 3)/(5*x + 7))^(x+1)',
    'x->∞',
    0
  ),
  (
    '8.2. lim ((2x+1)/(x-1))^(3x)',
    '((2*x + 1)/(x - 1))^(3*x)',
    'x->∞',
    0
  ),
  (
    '8.3. lim (2x+1)/(x-1)',
    '(2*x + 1)/(x - 1)',
    'x->∞',
    0
  ),
  (
    '8.4. lim ((3x+4)/(x+2))^(2x)',
    '((3*x + 4)/(x + 2))^(2*x)',
    'x->∞',
    0
  ),
  (
    '8.5. lim ((5x+7)/(2x+3))^(x+5)',
    '((5*x + 7)/(2*x + 3))^(x+5)',
    'x->∞',
    0
  ),
  (
    '8.6. lim ((x+1)/(3x+7))^(4x)',
    '((x + 1)/(3*x + 7))^(4*x)',
    'x->∞',
    0
  ),
  (
    '8.7. lim ((2x-1)/(x+3))^(x+2)',
    '((2*x - 1)/(x + 3))^(x+2)',
    'x->∞',
    0
  ),
  (
    '8.8. lim ((3x+2)/(x-5))^(3x+1)',
    '((3*x + 2)/(x - 5))^(3*x+1)',
    'x->∞',
    0
  );
