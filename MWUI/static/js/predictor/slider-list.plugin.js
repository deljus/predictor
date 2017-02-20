/**
 * Created by meowbetelgeuse on 07.02.17.
 *
 * jQuery плагин для отрисовки настроек в виде слайдеров
 * Для работы требует jQuery, bootstrap-slider.js
 *
 * Проект bootstrap-slider.js --> https://github.com/seiyria/bootstrap-slider
 *
 */
(function ($) {
    $.fn.listSettings = function (obj) {
        var methods = {
            /* инициализация плагина */
            init: function (params) {
                /* Дефолтные настройки плагина */
                var settings = $.extend({}, {
                    header: 'Undefined',
                    measure: '%',
                    min: 0,
                    max: 100,
                    step: 0.1,
                    value: 0,
                    handlerStyle: 'blue',
                    blockVal: 100,
                    tooltip: 'hide',
                    onSlide: function () {
                    }
                }, params);
                /* Создаем обьект DOM элементов */
                var dom = {
                    header: $('<span class="list-slider-text"></span>'),
                    measure: $('<span class="measure"></span>'),
                    sliderGroup: $('<div class="slider-group"></div>'),
                    badge: $('<span class="badge point-cursor"></span>'),
                    inputBd: $('<input class="input-badge" type="text" style="display:none"/>'),
                    sliderCon: $('<input class="ex" type="text" />').attr('data-slider-id', settings.handlerStyle),
                    error: $('<div class="alert alert-list alert-danger" role="alert" ><button type="button" class="close"> <span aria-hidden="true">&times;</span> </button><span class="text"></span></div>')
                };
                /* отрисовываем DOM элементы */
                dom.header.append(settings.header);
                dom.measure.append(' (' + settings.measure + ')');
                dom.header.append(dom.measure);
                dom.badge.append(settings.value);
                dom.sliderGroup.append([dom.badge, dom.sliderCon, dom.inputBd]);
                this.append([dom.header, dom.sliderGroup, dom.error]);

                /* создаем слайдер */
                dom.sl = dom.sliderCon.slider(settings);

                /* Закидываем DOM обьекты и настройки в data */
                this.data('dom', dom);
                this.data('settings', settings);

                /* Вешаем методы */
                dom.badge.on('click', $.proxy(methods.onClickBadge, this));
                dom.inputBd.on('keydown', function (e) {if (e.keyCode == 13) {$(this).trigger("blur")}});
                dom.inputBd.on('blur', $.proxy(methods.onBlurInput, this));
                dom.inputBd.bind("input", methods.onChangeInput);
                dom.sl.on("slide change", $.proxy(methods.slideSlider, this));
                dom.error.find("button").on('click', function () {dom.error.hide()});

                /* Возвращаем this для цепочек вызовов */
                return this;
            },

            /* Основные методы */

            /* Событие при клике на элемент badge
             * Скрываем badge и показываем input */
            onClickBadge: function () {

                var dom = this.data('dom');
                dom.inputBd.val(dom.badge.text());
                dom.badge.hide();
                dom.inputBd.show().select();
                dom.sl.slider("disable");
            },

            /* Событие при уходе фокуса с элемента input */
            onBlurInput: function () {
                var dom = this.data('dom'),
                    settings = this.data('settings'),
                    text = dom.inputBd.val();

                /* Проверяем входные данные на пустоту, превышение параметра и превышение блокировки */
                if (text.length == 0) {
                    methods.messageErr(dom, 'You entered an empty value. Please enter a number between ' + settings.min + ' and ' + settings.max + '.')
                } else if (text < settings.min || text > settings.max) {
                    methods.messageErr(dom, 'Please enter a number between ' + settings.min + ' and ' + settings.max + '.')
                } else if (text > settings.blockVal) {
                    methods.messageErr(dom, 'Please enter a number less or equal ' + settings.blockVal)
                } else {
                    /* Если все хорошо выставляем данные и двигаем слайдер */
                    text = Math.round(text * 10) / 10;
                    dom.badge.text(text).show();
                    dom.inputBd.hide();
                    dom.sl.slider("enable");
                    dom.sl.slider("setValue", text);
                    /* Вызываем Callback функцию изменения слайдера */
                    settings.onSlide.call(this);
                }
            },

            /* Вызов сообщения ошибки */
            messageErr: function (dom, text) {
                var err = dom.error.find(".text");
                err.empty();
                err.append(text);
                dom.error.fadeIn(300).delay(1500).fadeOut(800);
                dom.badge.show();
                dom.inputBd.hide();
                dom.sl.slider("enable");
            },

            /* Даем вводить цифры и точку с клавиатуры */
            onChangeInput: function () {
                if (this.value.match(/[^.0-9]/g)) {
                    this.value = this.value.replace(/[^.0-9]/g, '');
                }
            },

            slideSlider: function (slideEvt) {
                var value = slideEvt.value,
                    dom = this.data('dom'),
                    settings = this.data('settings');

                if(typeof value === 'object'){
                    value = slideEvt.value.newValue;
                }
                if (value < settings.blockVal) {
                    dom.badge.text(value);
                }
                else {
                    dom.sl.slider("setValue", settings.blockVal);
                    dom.badge.text(settings.blockVal);
                }
                settings.onSlide.call(this);
            },

            getValue: function () {
                var dom = this.data('dom');
                return {'handler': dom.header.text(), 'value': parseFloat(dom.badge.text())};
            },

            setValue: function (val) {
                var dom = this.data('dom');
                dom.sl.slider("setValue", val);
                dom.badge.text(val);
            },

            setBlock: function (val) {
                var settings = this.data('settings').blockVal = val;
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
            $.error('Метод "' + obj + '" не найден в плагине sliderList');
        }
    };
})(jQuery);