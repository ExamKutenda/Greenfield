
document.addEventListener("DOMContentLoaded", () => {
    document.body.style.opacity = 0;
    setTimeout(() => {
        document.body.style.transition = "opacity 0.6s ease";
        document.body.style.opacity = 1;
    }, 50);
});


document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("button, .btn").forEach(btn => {
        btn.addEventListener("mouseenter", () => {
            btn.style.boxShadow = "0 0 12px rgba(0, 200, 0, 0.6)";
        });
        btn.addEventListener("mouseleave", () => {
            btn.style.boxShadow = "none";
        });
    });
});


document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".add-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            btn.style.transform = "scale(0.9)";
            setTimeout(() => btn.style.transform = "scale(1)", 150);
        });
    });
});
