import { CellSlice, LocationSet, SlicedExecution, parse, slice } from "@andrewhead/python-program-analysis";

var source = `
import numpy as np
import pandas as pd
import random
import string
# Parameters
feature_columns = ["feat1", "feat2", "feat3", "feat4"]
value_generator = lambda x: np.random.uniform(0, 1, x)
num_samples = 100
word_len = 5
# Generate ids randomly
word = ''.join(random.choice(string.ascii_lowercase) for i in range(word_len))
ids = [f'{word}_{i}' for i in range(num_samples)]
df = pd.DataFrame({'id': ids})
df[feature_columns[0]] = value_generator(num_samples)
df[feature_columns[1]] = value_generator(num_samples)
df[feature_columns[2]] = value_generator(num_samples)
df[feature_columns[3]] = value_generator(num_samples)
print(df[feature_columns[0]].mean())
`

source = `
def complete_deg(n):
    a=np.zeros((n, n), int)
    np.fill_diagonal(a, n-1)
    matrix = np.matrix(a)
    return matrix    
a = complete_deg(5)
D.diagonal()
4*np.ones(5)
def complete_deg(n):
    a=np.zeros((n, n), int)
    np.fill_diagonal(a, n-1)
    return matrix    
def complete_deg(n):
    a=np.zeros((n, n), int)
    matrix = np.fill_diagonal(a, n-1)
    return matrix    
def complete_deg(n):
    a=np.zeros((n, n), int)
    np.fill_diagonal(a, n-1)
    return a    
4*np.ones(5)
def complete_adj(n):
    a=np.zeros((n, n), int)
    np.fill_diagonal(a, n-1)
    a = a.trapose
    return a
def complete_adj(n):
    a=np.zeros((n, n), int)
    a.fill(1)
    np.fill_diagonal(a, n-1)
    return a
def complete_adj(n):
    a=np.zeros((n, n), int)
    a.fill(1)
    np.fill_diagonal(a, 0)
    return a
complete_deg(3)
`

// [
// 'import pandas as pd',
// 'feature_columns = ["feat1", "feat2", "feat3", "feat4"]',
// 'value_generator = lambda x: np.random.uniform(0, 1, x)',
// 'num_samples = 100',
// "ids = [f'{word}_{i}' for i in range(num_samples)]",
// "df = pd.DataFrame({'id': ids})",
// 'df[feature_columns[0]] = value_generator(num_samples)',
// 'df[feature_columns[1]] = value_generator(num_samples)',
// 'df[feature_columns[2]] = value_generator(num_samples)',
// 'df[feature_columns[3]] = value_generator(num_samples)',
// 'print(df[feature_columns[0]].mean())'
// ]


function loc(line0, col0, line1 = line0 + 1, col1 = 0) {
    return { first_line: line0, first_column: col0, last_line: line1, last_column: col1 };
}

let ast = parse(source.trim());
let locations = slice(ast, new LocationSet(loc(ast.location.last_line - 1, 0)))
let splitSource = source.trim().split('\n');
// console.log(splitSource);

let splitSourceMap = new Map();
for (let idx = 0; idx < splitSource.length; idx++) {
    splitSourceMap.set(idx, false);
}

// Create array to sort
var locationArr = [];
for (var item in locations._items) {
    locationArr.push(item.split(",").map(x => parseInt(x)));
}

function compareLocations(a, b) {
    if (a[0] < b[0]) return -1;
    if (a[0] > b[0]) return 1;
    return 0;
}

locationArr.sort(compareLocations);
console.log(locationArr);

// For each element in the location array, index into the line list
// note that we are ignoring elem[1] and elem[3] here because we 
// are not calling .slice(elem[1], elem[3])
let nbgatherSlice = locationArr.flatMap((elem) => {
    var currSlice = [];

    // Check to see if slice is already included
    let beginIndex = elem[0] - 1;
    let endIndex = elem[3] === 0 ? elem[2] - 1 : elem[2];

    for (var i = beginIndex; i < endIndex; i++) {
        if (splitSourceMap[i] === true) {
            continue;
        }

        splitSourceMap[i] = true;
        currSlice.push(splitSource[i]);
    }

    return currSlice;
});

// Filters out any empty lines
nbgatherSlice = nbgatherSlice.join("\n").split(/\n/).filter(x => x.trim().length > 0);

console.log(nbgatherSlice);

