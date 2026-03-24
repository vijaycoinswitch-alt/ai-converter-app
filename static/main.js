document.addEventListener("DOMContentLoaded", () => {

    const fileInput = document.getElementById("file-input");
    const convertBtn = document.getElementById("convert-btn");
    const progressArea = document.getElementById("progress-area");
    const resultArea = document.getElementById("result-area");
    const downloadBtn = document.getElementById("download-btn");

    if (convertBtn && fileInput) {
        convertBtn.addEventListener("click", async () => {

            if (!fileInput.files.length) {
                alert("Please select file");
                return;
            }

            const formData = new FormData();
            formData.append("file", fileInput.files[0]);
            formData.append("type", convertBtn.dataset.type || "");

            progressArea.style.display = "block";
            resultArea.style.display = "none";

            try {
                const res = await fetch("/api/convert", {
                    method: "POST",
                    body: formData
                });

                const data = await res.json();

                progressArea.style.display = "none";

                if (data.success) {
                    resultArea.style.display = "block";
                    downloadBtn.href = data.download_url;
                }

            } catch (err) {
                alert("Error");
                console.error(err);
            }
        });
    }
});