
window.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sidebar--content span[title=Subscribe] ~ .break-all')
        .forEach(elem => elem.textContent = elem.textContent.replaceAll('-', ' ').replace(/^(Spot|Futures|OTC) /, ''));
    document.querySelectorAll('#operations span[title=subscribe] ~ .text-base')
        .forEach(elem => elem.textContent = elem.textContent.replaceAll('-', ' ').replace(/^(Spot|Futures|OTC) /, ''));

    let links = document.querySelectorAll('.aui-root .sidebar .sidebar--content button, .aui-root .sidebar .sidebar--content a');
    links.forEach(link => link.addEventListener('click', e => {
        links.forEach(o => o.classList.remove('active'));
        e.currentTarget.classList.add('active');
    }));

    // messages & schemas
    let elems = document.querySelectorAll('.sidebar--content > ul > li');
    for (let i = elems.length - 1; i >= 2; --i) {
        elems.item(i).remove();
    }
    let messages = document.getElementById('messages');
    if (messages) messages.remove();
    let schemas = document.getElementById('schemas');
    if (schemas) schemas.remove();
});