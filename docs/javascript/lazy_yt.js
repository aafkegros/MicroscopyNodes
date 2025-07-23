
document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".yt-lazy").forEach(function (el) {
      el.addEventListener("click", function () {
        var id = el.getAttribute("data-id");
        var params = el.getAttribute("data-params");
        var autoplay = "autoplay=1"
        if (params != "") {
          autoplay = "&autoplay=1"
        }
        var iframe = document.createElement("iframe");
        iframe.setAttribute("src", "https://www.youtube.com/embed/" + id + "?" + params + autoplay);
        iframe.setAttribute("frameborder", "0");
        iframe.setAttribute("allowfullscreen", "1");
        iframe.setAttribute("allow", "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" );
        iframe.style.width = "100%";
        iframe.style.height = "100%";
        el.innerHTML = "";
        el.appendChild(iframe);
      });
    });
  });