(function ($) {
    $.fn.chemEditor = function (obj) {
        var methods = {
            init: function (params) {
                var settings = $.extend({}, {
                    structure: 0,
                    models: [],
                    selectedModels: [{}],
                    additives: [],
                    selectAdditives: [{}],

                    temp: false,
                    tempRange: [200, 400],
                    tempStep: 1,
                    pres: false,
                    presRange: [0, 10],
                    presStep: 0.1,
                    modelsId: 0,

                    cml: false,
                    width: 500,
                    height: 410,
                    typeImg: 'png',
                    zoomMode: 'autoshrink',
                    backgroundColor: 'white',
                    defaultImage: 'static/predictor-start.svg',

                    typePres: 'default'


                }, params);


                var dom = {
                    container: $('<div class="maincontainer"></div>'),
                    image: {
                        container: $('<div class="col-md-7"></div>'),
                        body: $('<div class="image-container"></div>')
                    },
                    conf: {
                        container: $('<div class="col-md-5"></div>'),
                        body: $('<div class="conf"></div>')
                    }
                };

                this.data('dom', dom);
                this.data('settings', settings);


                dom.image.body.imageEdit(settings);
                if (settings.typePres == 'default') {
                    dom.conf.body.modelSelect(settings);
                } else if (settings.typePres == 'info') {
                    dom.conf.body.append(
                        "<h4>Start modelling</h4>" +
                        "<p>This application is for modeling the behavior of chemical structures and reactions " +
                        "under different conditions. Click on the image and add a structure of a substance " +
                        "or a reaction. After drawing the structure click on the 'Validate' button.</p><p>On the next page" +
                        " choose the conditions: model of reactions, temperature, pressure and etc," +
                        " press the 'Modelling' button</p>"
                    )
                }

                dom.image.container.append(dom.image.body);
                dom.conf.container.append(dom.conf.body);

                dom.container.append(dom.image.container);
                dom.container.append(dom.conf.container);
                this.append(dom.container);

                return this;

            },

            error: function () {

            },

            getSrtuct: function() {
                var settings = this.data('settings');
                return settings.structure;
            },

            getDataCVL: function () {
                dom = this.data('dom');
                return {data : dom.image.body.imageEdit('getCVL')};
            },

            getSettings: function () {
                dom = this.data('dom');
                data = dom.conf.body.modelSelect('getSettings');
                if (data == 1) {
                    return false;
                }
                else {
                    return data;
                }

            },

            getAllData: function () {
                var dom = this.data('dom'),
                    settings = this.data('settings'),
                    data = dom.image.body.imageEdit('getCVL'),
                    json = dom.conf.body.modelSelect('getSettings');
                json.data = data;
                json.structure = settings.structure;
                if (json.data) {
                    return json;
                }
            },

            destroy: function () {
                $(this).remove();
            }


        };


        if (methods[obj]) {
            return methods[obj].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof obj === 'object' || !obj) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Метод "' + obj + '" не найден в плагине jQuery');
        }
    };


})(jQuery);