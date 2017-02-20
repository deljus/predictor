/**
 * Created by meowbetelgeuse on 07.02.17.
 *
 * jQuery плагин для выбора моделей и растворителей
 * Для работы требует jQuery, bootstrap-slider.js, slider-list.plugin.js,
 * bootstrap-select.js
 *
 * Проект bootstrap-slider.js --> https://github.com/seiyria/bootstrap-slider
 * Проект bootstrap-select.js --> https://silviomoreto.github.io/bootstrap-select/
 */
(function ($) {
$.fn.modelSelect = function (obj) {
    var methods = {
        init: function (params) {
            var settings = $.extend({}, {
                models: [],
                selectedModels: [],
                additives: [],
                selectedAdditives:[],
                temp: false,
                tempRange: [200, 400],
                tempStep: 0.1,
                pres: false,
                presRange: [0, 10],
                presStep: 0.1,
                modelsId: 1
            }, params);

            var dom = {
                // dom model
                containerMC: $('<ul class="list-group-select list-group"></ul>'),

                model: {
                    title: $('<li class="list-title ">Models: </li>'),
                    body: $('<li class="list-select list-group-item"></li>'),
                    select: $('<select class="selectpicker" data-width="100%" multiple data-actions-box="false" title="Selected models of reactions"></select>'),
                },
                //dom condition
                condition:{
                    title: $('<li class="list-title ">Condition: </li>'),
                    temp: $('<li class="list-slider list-group-item controls controls-row"></li>'),
                    pres: $('<li class="list-slider list-group-item controls controls-row"></li>')
                },


                // dom Catalisators
                cat: {
                    container: $('<ul class="list-group-select list-group"></ul>'),
                    title: $('<li class="list-title ">Catalisators: </li>'),
                    select: $('<select class="selectpicker" data-width="100%" multiple data-actions-box="false" title="Selected catalisators"></select>'),
                    body: $('<li class="list-select list-group-item" ></li>'),
                },

                // dom Solvents
                solv: {
                    container: $('<ul class="list-group-select list-group"></ul>'),
                    title: $('<li class="list-title ">Solvents: </li>'),
                    body: $('<li class="list-select list-group-item" ></li>'),
                    select: $('<select class="selectpicker" data-width="100%" multiple data-actions-box="false" title="Selected solvents"></select>'),
                },

                total: {
                    container: $('<ul class="list-group-select list-group"></ul>'),
                    body: $('<li class="list-slider list-group-item controls controls-row total"></li>')
                }

            };

            var _this = this;

            dom.model.body.append(dom.model.select);
            dom.containerMC.append(dom.model.title);
            dom.containerMC.append(dom.model.body);



                dom.containerMC.append(dom.condition.title);

                dom.containerMC.append(dom.condition.temp.listSettings({
                    header: 'Temperature',
                    measure: 'K',
                    min: settings.tempRange[0],
                    max: settings.tempRange[1],
                    step: settings.tempStep,
                    value: settings.temp,
                    handlerStyle: 'red',
                    blockVal: settings.tempRange[1]
                }));

                dom.containerMC.append(dom.condition.pres.listSettings({
                    header: 'Pressure',
                    measure: 'atm',
                    min: settings.presRange[0],
                    max: settings.presRange[1],
                    step: settings.presStep,
                    value: settings.pres,
                    handlerStyle: 'red',
                    blockVal: settings.presRange[1]
                }));

            if(settings.models.length) {
                $.each(settings.models, function () {
                    if(settings.modelsId == this.type) {
                        if ($.inArray(this.model, settings.selectedModels) < 0) {
                            dom.model.select.append($('<option>' + this.name + '</option>').attr('model', this.model));
                        }
                        else {
                            dom.model.select.append($('<option selected>' + this.name + '</option>').attr('model', this.model));
                        }
                    }
                });
                dom.model.select.selectpicker('refresh');
            }
            else{
                dom.model.select.prop('disabled', true);
                dom.model.select.selectpicker('refresh');
            }

            this.append(dom.containerMC);


            dom.cat.body.append(dom.cat.select);
            dom.cat.container.append(dom.cat.title);
            dom.cat.container.append(dom.cat.body);



            dom.solv.body.append(dom.solv.select);
            dom.solv.container.append(dom.solv.title);
            dom.solv.container.append(dom.solv.body);

            dom.total.container.append(dom.total.body);


            this.data('dom',dom);
            this.data('settings',settings);

            var buffer = [];
            $.each(settings.selectedAdditives, function(additive){
                buffer.push(this.additive);
            });


            var selCat = [];
            var selSolv = [];

            var typeAddit = [dom.solv.select, dom.cat.select],
                contain = [dom.solv.container, dom.cat.container],
                data = [selSolv, selCat];

            if(settings.additives.length) {
                $.each(settings.additives, function () {
                    select = $.inArray(this.additive, buffer);
                    if (select < 0) {
                        typeAddit[this.type].append($('<option>' + this.name + '</option>').attr('additive', this.additive));
                    }
                    else {
                        amount = settings.selectedAdditives[select].amount;
                        typeAddit[this.type].append($('<option selected>' + this.name + '</option>').attr('additive', this.additive));
                        data[this.type].push({
                            additive: this.additive,
                            elem: methods.addSlideCat(this.name, amount, dom, this.type)
                        })
                    }
                });
                dom.solv.select.selectpicker('refresh');
                dom.cat.select.selectpicker('refresh');
            }
            else{
                $.each(typeAddit, function(){
                    this.prop('disabled', true);
                    this.selectpicker('refresh');
                })

            }


            dom.cat.select.data('selCat', data[1]);
            dom.solv.select.data('selSolv', data[0]);


            $.each(data[0], function(){
                this.elem.on("slide", {dom: dom},  methods.total)
            });

            methods.total({data:{dom:dom}});



            dom.solv.container.append(dom.solv.total);

            this.append(dom.cat.container);
            this.append(dom.solv.container);
            this.append(dom.total.container);

            dom.cat.select.on('hidden.bs.select', {dom: dom, type: 1}, methods.addAdditive);
            dom.solv.select.on('hidden.bs.select', {dom: dom, type: 0}, methods.addAdditive);
        },

        addSlideCat: function(name, amount, dom, type){
            var $slider = $('<li class="list-slider list-group-item controls controls-row"></li>');
            if(type == 0){
                $slider.listSettings({
                    header: name,
                    measure: '%',
                    min: 0,
                    max: 100,
                    step: 0.1,
                    value: amount * 100,
                    blockVal: 100,
                    onSlide: function(data){methods.total({data:{dom: dom}})}
                });

                dom.solv.container.append($slider);
            }
            else {
                $slider.listSettings({
                    header: name,
                    measure: 'ecv',
                    min: 0,
                    max: 6,
                    step: 0.1,
                    value: amount,
                    handlerStyle: 'green',
                    blockVal: 6,
                });
                dom.cat.container.append($slider);
            }

            return $slider;
        },

        total: function(e){
            var d = e.data.dom;
            var $newSlidersList =  d.solv.select.data('selSolv');//


            var sum = 0;
            $.each($newSlidersList, function (e,j) {
                sum += j.elem.listSettings('getValue').value;
            });
            var restValue = (100 - sum);
            if (restValue >= 0) {
                $.each($newSlidersList, function (e, j) {
                    var sliderValue = j.elem.listSettings('getValue').value;
                    j.elem.listSettings('setBlock', parseFloat(sliderValue) + parseFloat(restValue));
                });
            }
            d.total.body.text('Total = ' + sum  + ' %');
        },

        addAdditive: function(e){
            var val,
                name,
                $newList = [],
                $nameList = [],
                $oldList = [],
                dom,
                oldList = [],
                containerName;


            if(e.data.type == 1) {
                dom = e.data.dom;
                containerName = 'selCat';

            }
            else if(e.data.type == 0){
                dom = e.data.dom;
                containerName = 'selSolv';
            }
            oldList = $(this).data(containerName);


            $.each(oldList, function(){
                $oldList.push(this.additive);
            });

            $.each($(this).find("option:selected"), function(){
                val = parseInt($(this).attr('additive'));
                name = $(this).text();
                $newList.push(val);
                $nameList.push(name);
            });

            var len = $oldList.length - 1;
            var $oldListR = $oldList.reverse();

            $.each($oldListR, function(i,k){
                if($.inArray(k, $newList) < 0){
                    $(oldList[len-i].elem).remove();
                    oldList.splice(len-i,1)
                }
            });

            $.each($newList, function (i , k) {
                if($.inArray(k, $oldList) < 0){
                    oldList.push({additive : k, elem : methods.addSlideCat($nameList[i], 0, dom, e.data.type)});
                }
            });

            $(this).data(containerName, oldList);
            if(e.data.type == 0){methods.total({data:{dom: dom}})};


        },

        getSettings: function(models) {
            var dom = this.data('dom');

            var aditivesObj = [];
            var modelObj = [];

            $.each(dom.solv.select.data('selSolv'), function() {
                aditivesObj.push({additive: this.additive, amount : this.elem.listSettings('getValue').value / 100})
            });

            $.each(dom.cat.select.data('selCat'), function() {
                aditivesObj.push({additive: this.additive, amount : this.elem.listSettings('getValue').value})
            });

            $.each(dom.model.select.find("option:selected"), function() {
                modelObj.push({model : parseInt($(this).attr('model'))});
            })

            if(modelObj.length == 0){
                return 1;
            };


            var json = {
                temperature : String(dom.condition.temp.listSettings('getValue').value),
                pressure : String(dom.condition.pres.listSettings('getValue').value),
                additives :  aditivesObj,
                models: modelObj
            }
            return json;
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