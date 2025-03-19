////////////////////////////////////
// Helper functions for Dashboard //
////////////////////////////////////

/**
 * Finds all elements in the entire page matching `selector`, even if they are in shadowRoots.
 * Just like `querySelectorAll`, but automatically expand on all child `shadowRoot` elements.
 * @see https://stackoverflow.com/a/71692555/2228771
 */
function querySelectorAllShadows(selector, el = document.body) {
    // Recurse on childShadows.
    const childShadows = Array.from(el.querySelectorAll('*')).
        map(el => el.shadowRoot).filter(Boolean);

    const childResults = childShadows.map(child => querySelectorAllShadows(selector, child));
  
    // Fuse all results into singular, flat array.
    const result = Array.from(el.querySelectorAll(selector));
    return result.concat(childResults).flat();
}

/**
 * Finds the first Tabulator in the entire page matching `tabulator_class`,
 * even if they are in shadowRoots.
 */
function getTabulatorByClass(tabulator_class) {
    const tabulator_node = querySelectorAllShadows("." + tabulator_class)[0].
        shadowRoot.querySelectorAll("div.pnx-tabulator.tabulator")[0];
    
    return Tabulator.findTable(tabulator_node)[0];
}

/**
 * Filters `data` row-wise for `value`.
 */
function globalFilter(data, value) {
    const searchValueWords = value.toLowerCase().split(" ");
    const dataString = JSON.stringify(Object.values(data));
    return Object.values(searchValueWords).every((word) => {
        return String(dataString).toLowerCase().includes(word);
    });
}
