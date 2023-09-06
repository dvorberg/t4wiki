class FormControlManager
{
    constructor(parent, element)
    {
        this.parent = parent;
        this.element = element;

        this.original_value = this.value;

        element.addEventListener("change", this.on_change.bind(this))
    }

    get name()
    {
        return this.element.getAttribute("name");
    }

    get value()
    {
        return this.element.value;
    }
    
    on_change(event)
    {
        // Immediately notify the server.
        this.notify_server();
    }

    notify_server()
    {
        const self = this,
              script_url = `${globalThis.site_url}/articles/modify_upload.cgi`;

        var data = new FormData();
        data.append("article_id", this.parent.parent.article_id);
        data.append("upload_id", this.parent.upload_id);
        data.append("name", this.name);
        data.append("value", this.value);

        fetch(script_url, {
            "method": "POST",
            body: data
        }).then( function(response) {
            if (response.ok)
            {
                self.element.classList.remove("is-invalid");
                self.element.classList.add("is-valid");
            }
            else
            {
                self.element.classList.remove("is-valid");
                self.element.classList.add("is-invalid");


                response.text().then( text => { alert(text) });
            }
        });
    }
}

class CheckboxManager extends FormControlManager
{
    // pass
}

class TextInputManager extends FormControlManager
{
    constructor(parent, element)
    {
        super(parent, element);
        this.timeout = null;
    }
    
    on_change(event)
    {
        if (this.timeout)
        {
            clearTimeout(this.timeout);
            this.timeout = null;
        }

        if (this.value != this.original_value)
        {
            this.timeout = setTimeout(this.on_timeout.bind(this), 500);
        }
    }

    on_timeout(event)
    {
        this.timeout = null;
        this.notify_server();
        this.original_value = this.value;
    }
}

const TextareaManager = TextInputManager;

class UploadManager
{
    constructor(parent, element)
    {
        const self = this;
        
        this.parent = parent; 
        this.element = element;
        this.upload_id = parseInt(element.getAttribute("data-upload-id"));

        this.element.querySelectorAll("input,textarea").forEach(
            function(input) {
                var manager = null;
                if (input.tagName == "TEXTAREA")
                {
                    manager = new TextareaManager(self, input);
                }
                else
                {
                    const type = input.getAttribute("type");
                    if (type == "checkbox")
                    {
                        manager = new CheckboxManager(self, input);
                    }
                    else
                    {
                        manager = new TextInputManager(self, input);
                    }
                }

                var name = input.getAttribute("name") + "_manager";
                self[name] = manager;
            });
    }
}

class FileFormManager
{
    constructor(selector)
    {
        const self = this;
        
        this.root_element = document.querySelector(selector);
        this.article_id = parseInt(this.root_element.getAttribute(
            "data-article-id"));
        this.upload_managers = [];
        this.root_element.querySelectorAll(".upload").forEach(
            function(element) {
                self.upload_managers.push(new UploadManager(self, element));
            });
    }

}

export { FileFormManager };
