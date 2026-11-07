function renderSuggestions(data) {
  var list = document.querySelector(".suggestions");
  if (!list || !data || !data.suggestions) {
    return;
  }
  list.innerHTML = "";
  data.suggestions.forEach(function (text) {
    var item = document.createElement("li");
    item.textContent = text;
    list.appendChild(item);
  });
}
