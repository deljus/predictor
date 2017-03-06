(function ($) {

    var BASE_URL = window.location.protocol + "//" + window.location.host + "/",

        /* Server api urls */

        API = {
            createTask: BASE_URL + 'api/task/create/0',
            prepareTask: BASE_URL + 'api/task/prepare/',
            result: BASE_URL + 'api/task/model/',
            additives: BASE_URL + 'api/resources/additives',
            models: BASE_URL + 'api/resources/models',
            upload: BASE_URL + 'api/task/upload/0',
            resultTemplate: BASE_URL + 'static/delus/js/predictor/result.htm',
            saveTask: BASE_URL + 'api/task/results/'
        },

        /* Delay between requests */

        request = {
            timeOut : 400,
            increament : 400,
            count : 6
        },

        /* Pages and buttons is show and hide */

        $page = {
            indexPage: $("#index"),
            modelPage: $("#model"),
            resultPage: $("#result"),
            validButton: $("#validate"),
            revalidButton: $("#newstructure"),
            modellButton: $("#modelling"),
            loader: $("#loader"),
            errorMessage: $("#messange"),
            fileButton: $("#upload"),
            saveButton: $("#saving"),
            downloadButton: $("#downloading")
        },

        /* Server error massange */

        serverMassange = {
            modelError  : "<p>Unfortunately, we were unable to load the data. Maybe they just aren't ready. " +
            "To try again, click refresh <button class='btn btn-danger' onclick='window.location.reload()'><span class='glyphicon glyphicon-repeat'></span> Reload page</button></p>",
            error       :   "Heavy battles our server fell as a hero",
            fileUpload  :   "Could not load file",
            taskCreate  :   "Could not create new task",
            error403    :	"User access deny. you do not have permission to this task",
            error404    :	"Invalid task id. perhaps this task has already been removed",
            error406    :	"Task status is invalid. only validation tasks acceptable",
            error500    :	"Modeling server error"
        },

        /* Error messange */

        $messange = function(text, type) {
            $page.errorMessage.hide();
            $page.errorMessage.removeClass("alert-info","alert-warning","alert-danger","alert-success");
            if(type == 'error'){
                $page.errorMessage.addClass("alert-danger");
            }else if(type=='success'){
                $page.errorMessage.addClass("alert-success");
            }else if(type == 'info'){
                $page.errorMessage.addClass("alert-info");
            }else if(type == 'warning'){
                $page.errorMessage.addClass("alert-warning");
            }
            $page.errorMessage.find(".text").html(text);
            $page.errorMessage.fadeIn(300).delay(10000).fadeOut(800);
        };

    /* main page object */

    appPage = function () {

        var models,
            additives,
            task_model,
            templateData,
            self = this,
            result_task;

        return {
            init: function () {
                /* events of buttons */
                $page.validButton.on("click", this.onValidate);
                $page.modellButton.on("click", this.onModelling);
                $page.revalidButton.on("click", this.onRevalidating);
                $page.errorMessage.find("button").on('click', function () {$page.errorMessage.hide()});
                $page.fileButton.find('input[type=file]').on('change', this.prepareUpload);
                $page.saveButton.on("click", this.onSaving);
                /* Hide loader on load page */
                $(window).load(function () {$page.loader.hide();});
            },

            /* hide all pages and buttons */

            hideCom: function () {
                $.each($page, function (id, key) {
                    key.hide();
                })
            },

            /* Index page */

            index: function () {
                this.hideCom();
                $page.indexPage.html('').show();
                $page.validButton.show();
                $page.fileButton.show();

                /* create info chemdraw object if index page empty*/
                if(!$page.indexPage.html()) {
                    var obj = $('<div id="chemeditor" class="row"></div>').chemEditor({
                        onDefaultImage: function () {$page.validButton.prop('disabled', true);},
                        onChangeImage: function (data) {$page.validButton.prop('disabled', false);},
                        typePres: 'info'
                    });
                    $page.indexPage.append(obj);
                }

                $page.indexPage.show();

            },

            /* Load file */

            prepareUpload: function (event) {
                var data = new FormData($('#upload-file')[0]);

                $.ajax({
                    type: 'POST',
                    url: API.upload,
                    data: data,
                    dataType: 'json',
                    contentType: false,
                    cache: false,
                    processData: false,
                    success: function (data) {
                        window.location.href = '#/model/' + data.task + '/';
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        $messange('File upload error: ' + jqXHR.status + "-" + errorThrown);
                    }
                });

            },



            onValidate: function () {


                $page.validButton.button('loading');

                var dataObj = $("#chemeditor").chemEditor('getDataCVL');

                $.ajax({
                    url: API.createTask,
                    type: 'POST',
                    dataType: "json",
                    contentType: "application/json",
                    data: JSON.stringify(dataObj),
                    success: function (data) {
                        window.location.href = '#/model/' + data.task + '/';
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        $messange('Task creation error: ' + jqXHR.status + "-" + errorThrown, 'error');
                    },
                    complete: function () {
                        $page.validButton.button('reset');
                    }
                });
            },

            modelling: function (id) {
                task_model = id;
                console.log(task_model);
                this.hideCom();
                $page.loader.show();
                $page.modellButton.show();
                $page.modelPage.html('').show();

                $.when(
                    $.ajax(API.models, {type: 'GET'}),
                    $.ajax(API.additives, {type: 'GET'})
                ).done(function ($models, $additives) {

                    models = $models[0];
                    additives = $additives[0];
                    func(request.timeOut, request.increament, request.count);
                }).fail(function (jqXHR, textStatus, errorThrown) {
                    $messange('Models (Additives): ' + jqXHR.status + "-" + errorThrown, 'error');
                });


                function func(time, inc, count) {
                    $.get(API.prepareTask + id).done(function (data) {
                        $.each(data.structures, function (key, struct) {
                            var setting = {};
                            setting.additives = additives;
                            setting.models = models;
                            setting.selectedModels = struct.models[0];
                            setting.selectAdditives = struct.additives;
                            setting.cml = struct.data;
                            setting.modelsId = struct.type;
                            setting.temp = struct.temperature;
                            setting.pres = struct.pressure;
                            setting.structure = struct.structure;
                            setting.onChangeImage = function (data) {
                                $page.modellButton.hide();
                                $page.revalidButton.show();
                            };

                            var object = $('<div class="chemeditor row"></div>').chemEditor(setting);
                            $page.modelPage.append(object);
                        });
                        $page.loader.hide();
                    }).fail(function (jqXHR, textStatus, errorThrown) {

                        if (count > 0) {
                            count -= 1
                            time += inc;
                            setTimeout(function () {
                                func(time, inc, count)
                            }, time);

                            console.log(jqXHR.status +'-' + textStatus + '' + errorThrown)

                        } else {
                            $page.modelPage.append(serverMassange.modelError);
                            $page.loader.hide();
                        }




                    })

                }

            },

            onModelling: function () {

                var obj1 = [],
                    flag = true;


                $.each($(".chemeditor"),function() {
                    var e = $(this).chemEditor('getAllData');
                    if(e){
                        obj1.push(e)
                    }
                    else{
                        flag = false
                    }
                });



                if (flag) {
                    $page.modellButton.button('loading');
                    $.ajax({
                        url: API.result + task_model,
                        type: 'POST',
                        data: JSON.stringify(obj1),
                        success: function (data) {
                            window.location.href = '#/result/' + data.task + '/';
                        },
                        error: function (data) {


                        },
                        complete: function () {
                            $page.modellButton.button('reset');
                        }
                    });
                }
                else {
                    $messange("Please make sure that the model field is filled and the total percentage of the solvent is equal to 100 (if the solvent is selected)", 'error');
                }
            },

            resulting: function (id, typePage) {

                var url;
                if(typePage == 'result'){
                    url = API.result;
                }else if(typePage == 'history'){
                    url = API.saveTask
                }

                this.hideCom();
                $page.resultPage.html('').show();
                $page.loader.show();

                var tempData;

                var _this = this;

                function func(time, inc, count) {
                    $.get(url + id).done(function (data) {
                        result_task = id;

                        $.ajax(API.resultTemplate, {type: 'GET'}).done(function(tmpData) {

                            $page.saveButton.show();
                            $page.downloadButton.show();


                            MarvinJSUtil.getPackage("marvinjs-iframe").then(function (marvinNameSpace) {
                                marvinNameSpace.onReady(function () {
                                    marvin = marvinNameSpace;
                                    Handlebars.registerHelper("inc", function (value, options) {
                                        return parseInt(value) + 1;
                                    });

                                    Handlebars.registerHelper("base", function (value, options) {
                                        var bs64 = marvin.ImageExporter.mrvToDataUrl(value, "png", {width: 500,
                                            height: 410,
                                            zoomMode: 'autoshrink'});
                                        return new Handlebars.SafeString('<img src="' + bs64 + '" class="image">');
                                    });

                                    var template = Handlebars.compile(tmpData);
                                    var html = template(data);

                                    $page.resultPage.append(html);

                                    $page.loader.hide();


                                });


                            });

                        });
                    }).fail(function () {
                        console.log(time + '-' + inc + '-' + count);
                        if (count > 0) {
                            count -= 1;
                            time += inc;
                            setTimeout(function () {
                                func(time, inc, count)
                            }, time);
                        } else {
                            $page.resultPage.append(serverMassange.modelError);
                            $page.loader.hide();
                        }

                    })
                }


                func(request.timeOut, request.increament, request.count);
            },



            onRevalidating: function () {
                $page.revalidButton.button('loading');
                var obj1 = $(".chemeditor").chemEditor('getDataCVL');
                var struct = $(".chemeditor").chemEditor('getSrtuct');
                obj1.structure = struct;
                $.ajax({
                    url: API.prepareTask + task_model,
                    type: 'POST',
                    data: JSON.stringify([obj1]),
                    success: function (data) {
                        $page.loader.hide();
                        $page.revalidButton.button('reset');
                        window.location.href = '#/model/' + data.task + '/';
                    },
                    error: function (data) {
                        $page.revalidButton.button('reset');
                        $page.loader.hide();
                    },
                    complete: function () {
                    }
                });
            },

            onSaving: function() {
                $page.saveButton.button('loading');
                $.ajax({
                    url: API.saveTask + result_task,
                    type: 'POST',
                    contentType: "application/json",
                    success: function (data) {
                        $page.saveButton.prop('disabled', true);
                        $messange('Task saved', 'success');
                    },
                    error: function (jqXHR, textStatus, errorThrown) {
                        $messange('Task save error: ' + jqXHR.status + "-" + errorThrown, 'error');
                    },
                    complete: function () {
                        $page.saveButton.button('reset');
                    }
                });
            }

        }
    };


    var app = appPage();
    app.init();

    $.routes.add('/index/', function () {
        app.index()
    });
    $.routes.add('/model/{id:string}/', function () {
        app.modelling(this.id);
    });
    $.routes.add('/result/{id:string}/', function() {
        app.resulting(this.id, 'result');
    });
    $.routes.add('/history/{id:string}/', function() {
        app.resulting(this.id, 'history')
    });

    if (window.location.hash == '') {
        window.location.href = "#/index/"
    }

})(jQuery, window);

