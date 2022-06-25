import { CellSlice, LocationSet, SlicedExecution, parse, slice } from "@andrewhead/python-program-analysis";
import sqlite3 from 'sqlite3';
import fs from "file-system";
import { strict as assert } from 'assert';

function loc(line0, col0, line1 = line0 + 1, col1 = 0) {
    return { first_line: line0, first_column: col0, last_line: line1, last_column: col1 };
}

let traceID = process.argv[process.argv.length - 4];
let sessionID = process.argv[process.argv.length - 3];
let cellToRerun = process.argv[process.argv.length - 2];
let validCounters = process.argv[process.argv.length - 1];

const db = new sqlite3.Database('./data/traces.sqlite');
let sql = "select source from cell_execs where trace=" + traceID + " and session=" + sessionID + " and counter in (" + validCounters + ") order by counter";

function compareLocations(a, b) {
    if (a[0] < b[0]) return -1;
    if (a[0] > b[0]) return 1;
    return 0;
}

db.all(sql, [], (err, rows) => {

    // Create AST
    let source = rows.map(elem => elem.source.trim());
    let splitSource = source.join('\n').trim().split('\n');
    let ast = parse(source.join('\n').trim());
    console.log(source);

    // Slice each line and compute deps
    let linenos = Array.from(Array(ast.location.last_line - 1), (_, index) => index + 1);
    let cellnos = Array.from(Array(source.length), (_, index) => index + 1);

    let dependencies = new Map(linenos.map((lineno) => {
        let locations = slice(ast, new LocationSet(loc(lineno, 0, lineno, 1000)));

        let splitSourceMap = new Map();
        for (let idx = 0; idx < splitSource.length; idx++) {
            splitSourceMap.set(idx, false);
        }

        // Create array to sort
        var locationArr = [];
        for (var item in locations._items) {
            locationArr.push(item.split(",").map(x => parseInt(x)));
        }

        locationArr.sort(compareLocations);
        // console.log(locationArr);

        // For each element in the location array, index into the line list
        // note that we are ignoring elem[1] and elem[3] here because we 
        // are not calling .slice(elem[1], elem[3])
        let nbgatherSlice = locationArr.flatMap((elem) => {
            var currSlice = [];

            // Check to see if slice is already included
            let beginIndex = elem[0] - 1;
            let endIndex = elem[3] === 0 ? elem[2] - 1 : elem[2];

            // console.log(beginIndex);
            // console.log(endIndex);

            for (var i = beginIndex; i < endIndex; i++) {
                if (splitSourceMap[i] === true) {
                    continue;
                }

                splitSourceMap[i] = true;
                currSlice.push(i);
            }

            return currSlice;
        });

        return [lineno, nbgatherSlice]
    }));

    // console.log(dependencies);

    // Find lines in cellToRerun, 1 indexed
    let cellToRerunStart = source.slice(0, cellToRerun - 1).join('\n').split(/\n/).filter(x => x.trim().length > 0).length + 1;
    let cellToRerunEnd = cellToRerunStart - 1 + source[cellToRerun - 1].trim().split(/\n/).filter(x => x.trim().length > 0).length;

    assert.deepEqual(cellToRerunStart <= cellToRerunEnd, true, "end is less than start");

    // assert here that cell is expected
    let slicedCell = splitSource.slice(cellToRerunStart - 1, cellToRerunEnd).join('\n').trim();
    console.log(dependencies)
    console.log(slicedCell)
    console.log(source[cellToRerun - 1])
    console.log(cellToRerunStart)
    console.log(cellToRerunEnd)
    console.log(splitSource[cellToRerunStart - 1])

    assert.deepEqual(slicedCell, source[cellToRerun - 1], "Cell is not expected.");

    // Iterate through values
    var forwardSliceLines = new Set();
    for (let [lineno, deps] of dependencies) {
        for (const dep of deps) {
            if (cellToRerunStart <= dep + 1 && dep + 1 <= cellToRerunEnd) {
                forwardSliceLines.add(lineno);
                break;
            }
        }
    }

    forwardSliceLines = Array.from(forwardSliceLines).map(Number).sort(function (a, b) { return a - b });

    // Create forward slice (line list is offset by 1)
    var forwardSlice = [];
    for (const line of forwardSliceLines) {
        forwardSlice.push(splitSource[line - 1]);
    }


    // Filters out any empty lines
    forwardSlice = forwardSlice.join("\n").split(/\n/).filter(x => x.trim().length > 0);

    let numLinesNeeded = forwardSlice.length;
    fs.appendFileSync('eda/forward/results/nbgather_stats.txt', "(" + traceID + ", " + sessionID + ", " + numLinesNeeded + ")\n");

    // Write out slice
    let sliceFilename = 'eda/forward/results/nbgather/' + traceID + '_' + sessionID + '.txt';
    fs.writeFileSync(sliceFilename, forwardSlice.join("\n"));
})