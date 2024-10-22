
document.getElementById('copySyntax').addEventListener('click', copySyntaxToClipboard);

function copySyntaxToClipboard() {
    const codeBox = document.querySelector('#syntax-box');
    const range = document.createRange();
    range.selectNode(codeBox);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);

    try {
        const successful = document.execCommand('copy');
        if (successful) {
        alert('Syntax copied successfully!');
        }
    } catch (err) {
        console.log('Unable to copy code.');
    }

    window.getSelection().removeAllRanges();
}

document.getElementById('copyWebhook').addEventListener('click', copyWebhookToClipboard);

function copyWebhookToClipboard() {
    const codeBox = document.querySelector('#webhook');
    const range = document.createRange();
    range.selectNode(codeBox);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);

    try {
        const successful = document.execCommand('copy');
        if (successful) {
        alert('✅ Webhook URL copied successfully!');
        }
    } catch (err) {
        console.log('Unable to copy code.');
    }

    window.getSelection().removeAllRanges();
}



function showAlert(obj) {
    var script_type = obj.value;
    var alert_type = document.getElementById("alert_type");
    var alert_type_label = document.getElementById("alert_type_label");
    if (script_type === "INDICATOR") {
        alert_type.style.display = "block";
        alert_type_label.style.display = "block";
    }
    if (script_type === "STRATEGY") {
        alert_type.style.display = "none";
        alert_type_label.style.display = "none";
    }
}