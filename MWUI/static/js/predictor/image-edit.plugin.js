(function ($) {
    "use struct";
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
                    defaultImage: 'start.svg',
                    onDefaultImage: function () {
                    },
                    onChangeImage: function () {
                    }
                }, params);
                var dom = {
                    img: $("<img class='image'>").attr({src: settings.defaultImage}),
                    error: $('<div class="alert alert-list alert-danger" role="alert" ><button type="button" class="close"> <span aria-hidden="true">&times;</span> </button><span class="text"></span></div>')
                };

                this.data('dom', dom);
                this.data('settings', settings);
                this.data('flag', false);


                var _this = this;
                var marvin, marvinSketcherInstance;

                $('#close-wo-save').click(function() {
                    $("#myModal").css({'z-index' : -40, opacity: 0, 'background' : 'rgba(0,0,0,0)'});
                    $("body").removeClass('modal-open');
                });



                MarvinJSUtil.getPackage("marvinjs-iframe").then(function (marvinNameSpace) {
                    marvinNameSpace.onReady(function () {

                        marvin = marvinNameSpace;
                        try {
                            if (settings.cml) {
                                var base64 = marvin.ImageExporter.mrvToDataUrl(settings.cml, settings.typeImg, settings);
                                dom.img.attr({"src": base64, "alt": settings.cml});
                                console.log(base64);
                                _this.append(dom.img);
                            }
                            else {
                                _this.append(dom.img);
                            }

                        } catch (err) {
                            console.log(err)


                        }


                    });
                }, function () {
                    alert("Cannot retrieve marvin instance from iframe");
                });

                MarvinJSUtil.getEditor("marvinjs-iframe").then(function (sketcherInstance) {
                    marvinSketcherInstance = sketcherInstance;
                    _this.click(function () {
                        $("#myModal").css({'z-index' : 1050, 'opacity': 1, 'background': 'rgba(0,0,0,.5)'});
                        $("body").addClass('modal-open');
                        marvinSketcherInstance.importStructure("mrv", dom.img.attr('alt'));
                        _this.data('flag', true);
                    });


                    $('#close-modal').click(function () {
                        if (_this.data('flag')) {
                            marvinSketcherInstance.exportStructure("mrv").then(function (s) {
                                dom.img.attr('alt', s);
                                console.log(s);
                                if (s == '<cml><MDocument></MDocument></cml>') {
                                    dom.img.attr('src', settings.defaultImage)
                                    settings.onDefaultImage.call()
                                }
                                else {
                                    var src = marvin.ImageExporter.mrvToDataUrl(s, settings.typeImg, settings);
                                    dom.img.attr('src', src);
                                    settings.onChangeImage.call(src);
                                }

                                _this.data('flag', false)
                                $("#myModal").css({'z-index' : -40, opacity: 0, 'background' : 'rgba(0,0,0,0)'});

                            });
                        }
                    });
                }, function () {
                    alert("Cannot retrieve sketcher instance from iframe");
                });

                return this;
            },

            getCVL: function () {
                var img = this.data('dom').img
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
})(jQuery,window,document);