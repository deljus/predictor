(function ($) {

     var BASE_URL = window.location.protocol + "//" + window.location.host + "/",
     API = {
         createTask : BASE_URL + 'api/task/create/0',
         prepareTask : BASE_URL + 'api/task/prepare/',
         result : BASE_URL + 'api/task/model/',
         additives : BASE_URL + 'api/resources/additives',
         models : BASE_URL + 'api/resources/models'
     };

    var app1 = function() {

        var $page = {
            indexPage   : $("#index"),
            modelPage   : $("#model"),
            resultPage  : $("#result"),
            validButton : $("#validate"),
            revalidButton   : $("#newstructure"),
            modellButton: $("#modelling"),
            loader      : $("#loader"),
            errorMessage: $("#error-messange"),
            fileButton  : $("#upload")
        };

        var serverError = "<p>Unfortunately, we were unable to load the data. Maybe they just aren't ready. " +
            "To try again, click refresh <span class='glyphicon glyphicon-repeat'></span></p>";

        var timeOut = 400,
            increament = 400,
            count = 6;

        var model,
            additives,
            obj,
            task_model;

        return {
            init: function () {
                $.when(
                    $.ajax(API.models, {type: 'GET'}),
                    $.ajax(API.additives, {type: 'GET'})
                ).done(function ($models, $additives) {
                    models = $models[0];
                    additives = $additives[0];
                }).fail(function () {
                    $("#draw").append("Сервер не отвечает((((")
                });

                obj = $('<div id="chemeditor"></div>').chemEditor({
                    onDefaultImage: function () {
                        $page.validButton.prop('disabled', true);
                    },
                    onChangeImage: function (data) {
                        $page.validButton.prop('disabled', false);
                    },
                    typePres: 'info'
                });

                $page.indexPage.append(obj);
                $page.validButton.show();

                $page.validButton.on("click", this.onValidate);
                $page.modellButton.on("click", this.onModelling);
                $page.revalidButton.on("click", this.onRevalidating);
                $page.errorMessage.find("button").on('click', function () {
                    $page.errorMessage.hide()
                });
                $page.fileButton.on("click", function() {

                    $.FileDialog();

                    });


                    $(window).load(function() {
                    $page.loader.hide();
                });

            },

            hideCom: function() {
                $.each($page, function(id, key) {
                    key.hide();
                })
            },



            index: function () {
                this.hideCom();
                $page.indexPage.show();
                $page.validButton.show();
                $page.fileButton.show();
            },

            onValidate:function() {
                $page.validButton.button('loading');

                var dataObj = $("#chemeditor").chemEditor('getDataCVL');

                $.ajax({
                    url: API.createTask,
                    type: 'POST',
                    dataType: "json",
                    contentType: "application/json",
                    data: JSON.stringify(dataObj),
                    success: function (data) {
                        $page.validButton.button('reset');
                        window.location.href = '#/model/' + data.task + '/';
                    },
                    error: function (data) {
                    },
                    complete: function () {
                    }
                });
            },

            modelling: function (id) {
                task_model = id;
                this.hideCom();
                $page.loader.show();
                $page.modellButton.show();
                $page.modelPage.html('').show();

                function func(time, inc, count) {
                    $.get(API.prepareTask + id).done(function (data) {
                        var setting = {};
                        setting.additives = additives;
                        setting.models = models;
                        setting.cml = data.structures[0].data;
                        setting.modelsId = data.structures[0].type;
                        setting.temp = data.structures[0].temperature;
                        setting.pres = data.structures[0].pressure;
                        setting.structure = data.structures[0].structure;
                        setting.onChangeImage = function (data) {
                            $page.modellButton.hide();
                            $page.revalidButton.show();
                        };

                        var object = $('<div class="chemeditor col-lg-12"></div>').chemEditor(setting);
                        $page.modelPage.append(object);

                        $page.loader.hide();
                    }).fail(function () {
                        console.log(time + '-' + inc + '-' + count);
                        if(count > 0) {
                            count -= 1;
                            time += inc;
                            setTimeout(function(){func(time, inc, count)}, time);
                        }else{
                            $page.modelPage.append(serverError);
                            $page.loader.hide();
                        }

                    })

                }

               func(timeOut,increament,count);

            },

            onModelling: function() {

                var obj1 = $(".chemeditor").chemEditor('getAllData');


                if(obj1) {
                    $page.loader.show();
                    $page.modellButton.button('loading');
                    $.ajax({
                        url: API.result + task_model,
                        type: 'POST',
                        data: JSON.stringify([obj1]),
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
                else{
                    $page.errorMessage.find(".text").html("Please make sure that the model field is filled and the total percentage of the solvent is equal to 100 (if the solvent is selected)");
                    $page.errorMessage.fadeIn(300).delay(4000).fadeOut(800);
                }
            },

            resulting: function(id) {

                this.hideCom();
                $page.resultPage.html('').show();
                $page.loader.show();
                function func(time, inc, count) {

                    $.get(API.result + id).done(function (data) {
                        $page.loader.hide();
                        $page.resultPage.append(JSON.stringify(data));

                    }).fail(function () {
                        console.log(time + '-' + inc + '-' + count);
                        if(count > 0) {
                            count -= 1;
                            time += inc;
                            setTimeout(function(){func(time, inc, count)}, time);
                        }else{
                            $page.resultPage.append(serverError);
                            $page.loader.hide();
                        }

                    })
                }


                func(timeOut,increament,count);
            },

            onRevalidating: function() {
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
            }

        }
    };




    var app = app1();
    app.init();

    $.routes.add('/index/', function(){app.index()});
    $.routes.add('/model/{id:string}/', function() {
        app.modelling(this.id);
    });
    $.routes.add('/result/{id:string}/', function() {
        app.resulting(this.id);
    });

    if(window.location.hash == '') {
        window.location.href = "#/index/"
    }

})(jQuery);

