(function ($) {
    $.fn.imageEdit = function (obj) {
        var methods = {
            init: function (params) {
                var settings = $.extend({}, {
                    cml: false,
                    width: 500,
                    height: 410,
                    typeImg: 'png',
                    zoomMode: 'autoshrink',
                    backgroundColor: 'white',
                    defaultImage: 'img/start.svg',
                    onDefaultImage: function () {
                    },
                    onChangeImage: function () {
                    }
                }, params);
                var dom = {
                    img: $("<img class='image' alt='<cml><MDocument></MDocument></cml>'>").attr({src: settings.defaultImage}),
                    error: $('<div class="alert alert-list alert-danger" role="alert" ><button type="button" class="close"> <span aria-hidden="true">&times;</span> </button><span class="text"></span></div>')
                };

                this.data('dom', dom);
                this.data('settings', settings);
                this.data('flag', false);

                var marvin;
                var _this = this;


                MarvinJSUtil.getPackage("marvinjs-iframe").then(function (marvinNameSpace) {
                    marvinNameSpace.onReady(function () {

                        marvin = marvinNameSpace;


                  


                        if (settings.cml) {
                            var params = {
                                'inputFormat': settings.cml
                            };
                            var base64;
                            base64 = marvin.ImageExporter(params);
                            console.log(base64);
                            dom.img.attr({"src": base64, "alt": settings.cml});
                            _this.append(dom.img);
                        }
                        else {
                            _this.append(dom.img);
                        }
                    })
                });

                MarvinJSUtil.getEditor("marvinjs-iframe").then(function (sketcherInstance) {
                    marvinSketcherInstance = sketcherInstance;

                    _this.click(function () {
                        $("#myModal").modal({'backdrop': 'static'});
                        marvinSketcherInstance.importStructure("mrv", dom.img.attr('alt'));
                        _this.data('flag', true);
                    });


                    $('#close-modal').click(function () {
                        if (_this.data('flag')) {
                            marvinSketcherInstance.exportStructure("mrv").then(function (s) {
                                dom.img.attr('alt', s);
                                if (s == '<cml><MDocument></MDocument></cml>') {
                                    dom.img.attr('src', settings.defaultImage);
                                    settings.onDefaultImage.call()
                                }
                                else {
                                    var src = marvin.ImageExporter.mrvToDataUrl(s, settings.typeImg, settings);
                                    dom.img.attr('src', src);
                                    settings.onChangeImage.call(src);
                                }

                                _this.data('flag', false);
                                $("#myModal").modal('hide');

                            });
                        }
                    });
                });

                return this;
            },

            getCVL: function () {
                var img = this.data('dom').img;
                return unescape($(img).attr('alt'));
            },
            destroy: function () {
                this.remove();
            }
        };


        if (methods[obj]) {
            return methods[obj].apply(this, Array.prototype.slice.call(arguments, 1));
        } else if (typeof obj === 'object' || !obj) {
            return methods.init.apply(this, arguments);
        } else {
            $.error('Метод "' + obj + '" не найден в плагине jQuery.mySimplePlugin');
        }
    };
})(jQuery);