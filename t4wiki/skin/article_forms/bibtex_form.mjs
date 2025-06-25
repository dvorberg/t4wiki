class TemplateButton
{
	constructor(pre)
	{
		this.type = pre.getAttribute("data-type");
		this.template = pre.innerText;
		
		const button = document.createElement("button");
		button.classList.add("btn")
		button.classList.add("btn-link")
		button.innerText = this.type;
		button.setAttribute("id", this.type);
		
		const button_container = document.querySelector(".template-buttons");
		button_container.append(button);
		this.button = button_container.querySelector("#" + this.type);
		this.button.addEventListener("click", this.onclick.bind(this));
	}

	onclick(event)
	{
		const ta = document.querySelector(".source-viewer");
		ta.jar.updateCode(this.template + ta.textContent);
		event.preventDefault();
		return false;		
	}
}

document.addEventListener("DOMContentLoaded", function(event) {
	document.querySelectorAll(".bibtex-templates > pre").forEach(pre => {
		new TemplateButton(pre);
	});
});

