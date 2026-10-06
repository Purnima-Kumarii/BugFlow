fetch("sidebar.html")
    .then(response => response.text())
    .then(data => {
        document.getElementById("sidebar").innerHTML = data;
    })
    .catch(error => {
        console.error("Sidebar loading error:", error);
    });