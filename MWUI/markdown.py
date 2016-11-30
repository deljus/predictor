from misaka import HtmlRenderer


class CustomMisakaRenderer(HtmlRenderer):
    def table(self, content):
        return '<table class="table">{}</table>'.format(content)
