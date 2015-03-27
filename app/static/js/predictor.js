var marvinSketcherInstance;
var isSaveMrvBtnExists=false;
$(document).ready(function handleDocumentReady (e) {
	initControl();
	MarvinJSUtil.getEditor("#sketch").then(function (sketcherInstance) {
		marvinSketcherInstance = sketcherInstance;
	},function (error) {});
	
	MarvinJSUtil.getPackage("#sketch").then(function (marvinNameSpace) {
		marvinNameSpace.onReady(function () {
			marvin = marvinNameSpace;
		});
	}, function () {
		alert("Cannot retrieve marvin instance from iframe");
	});	

});

/*** debug fuctions ***/
function set_task(task_id)
{
	$('#task_id').val(task_id);	
}
function get_task()
{
	return 	$('#task_id').val();
}
function load_reactions()
{
	hide_all();
	load_task_reactions(get_task());		
}

function load_results()
{
	hide_all();
	load_modelling_results(get_task());		
}

function map_done()
{
	set_task_status(get_task(),MAPPING_DONE)	
}

function model_done()
{
	set_task_status(get_task(),MODELLING_DONE)	
}


var Progress = {}
Progress.increase_progress = function(value){
	
	console.log('increase_progress->');
	try {	
		var jPrg= $('.progress div[role=progressbar]');
		if (value)
			var prc = value;
		else
		{
			var prc = parseInt(jPrg.attr('aria-valuenow'));
			if (prc>=90)
				prc = 0;
				
			prc+=10;				
		}
		

		jPrg.attr('aria-valuenow', prc);
		jPrg.width(prc+'%').text(prc+'%');	
	}
	catch(err){
		console.log(err);
	}
}

Progress.start = function(){
	$('.progress').show();
	this.timer_id = setInterval(this.increase_progress, 1000);
}

Progress.done = function(){
	clearInterval(this.timer_id);
	this.increase_progress(100);
	setTimeout(function(){$('.progress').hide()}, 1000);	
} 

function handleRequestError()
{
    Progress.done();
}

function download_results(format)
{
	var task_id = $('#task_id').val();
	window.open('/download/'+task_id+'?format='+format);	
}

function select_mode(mode)
{
	hide_all();
    switch(mode)
    {
        case 'file':
			hide_editor();
			show_file_upload();	
			
            break;
        case 'editor':
			hide_file_upload();
            show_editor(true);
            break;

    }
}

function upload_file(data)
{
       return  $.ajax({
            type: 'POST',
            url: '/upload',
            data: data,
            contentType: false,
            cache: false,
            processData: false,
            async: false,
        });	
	
}

function upload_task_file_data()
{
	console.log('upload_task_file_data->');
	Progress.start();
			
	var form_data = new FormData($('#upload-file-form')[0]);	
	upload_file(form_data).done(function (data, textStatus, jqXHR) {

		hide_file_upload();
		
        $("#task_id").val(data);
        start_task_mapping(data);

    }).fail(handleRequestError);
}


$(function() {
    $('#upload-file-btn').click(function() {

        if ($('#file').val()=='')
        {
            alert('You have to select file');
            return false;
        }
		upload_task_file_data();
    });
});

function isEmpty(val)
{
    if (val=='' || val==undefined || val=='undefined' || val==null || val=='null')
        return true;
    else
        return false;
}


function isMolEmpty(data)
{
    if ( String(data).indexOf('MChemicalStruct')>=0 || String(data).indexOf('$RXN')>=0)
        return false;
    else
        return true;
}

function set_task_status(task_id, status)
{
    console.log('set_task_status->'+status);
    var data =  JSON.stringify({"task_status": status});
    return $.ajax({
        "url": "/task_status/"+task_id
        ,"type": "PUT"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": data
    });
}

function get_task_status(task_id)
{
	console.log('get_task_status->'+task_id);
    return $.get("/task_status/"+task_id);
}

function get_reaction_structure(reaction_id)
{
    return $.get("/reaction_structure/"+reaction_id);
}

function put_reaction_structure(reaction_id, data)
{ 
    console.log('put_reaction_structure->');
    var data = {"reaction_structure": data};

    return $.ajax({
            "url": "/reaction_structure/"+reaction_id
            ,"type": "POST"
            ,"dataType": "json"
            ,"contentType": "application/json"
            ,"data": data
    }); 	
}

function get_models(model_hash)
{
    data = {"hash": model_hash};
    return $.get("/models", data);
}

function get_solvents()
{
    return $.get("/solvents");
}

function get_reactions_by_task(task_id)
{
    return $.get("/task_reactions/"+task_id)
}

/******************************************************/
TASK_CREATED    = 0
REQ_MAPPING     = 1
LOCK_MAPPING    = 2
MAPPING_DONE    = 3
REQ_MODELLING   = 4
LOCK_MODELLING  = 5
MODELLING_DONE  = 6

var TIMER_INTERVAL = 7000;
var MOL_FORMAT = 'mrv';

var TAMER_ID;

/******************************************************/

function initControl ()
{
	// get mol button
	$("#btn-upload-sketcher-data").on("click", function (e) {
        upload_sketcher_data();
	});
}

function hide_all()
{
	hide_select_mode();
	hide_editor();
	hide_reactions();
	hide_file_upload();
	hide_modelling_results();
	
}

function hide_modelling_results()
{
	$('#results-div').hide();	
}

function hide_select_mode()
{
    $('#select-mode-div').hide(1000);
}
function hide_upload_sketcher_data_btn()
{
	$('#btn-upload-sketcher-data-div').hide();	
}

function hide_editor()
{
	$('#editor-div').hide();	
}

function show_editor(show_upload_reaction_button)
{
	$('#editor-div').show(1000);
	if (show_upload_reaction_button)
		$('#btn-upload-sketcher-data-div').show();
}

function hide_reactions()
{
	$('#reactions-div').hide();	
}

function hide_file_upload()
{
	$('#file-upload-div').hide();	
}

function show_file_upload()
{
	$('#file-upload-div').show(1000);	
}

function upload_sketcher_data()
{
	    Progress.start();
		marvinSketcherInstance.exportStructure(MOL_FORMAT).then(function(source) {


            if (isMolEmpty(source))
            {
                alert('You need enter a reaction');
				Progress.done();
                return false;
            }
            else
                upload_task_draw_data(source);

		}, function(error) {
			alert("Molecule export failed:"+error);
		});
}


function upload_task_draw_data(draw_data)
{
    console.log('upload_task_draw_data->');
	hide_upload_sketcher_data_btn();

    var data = JSON.stringify({"reaction_structure": draw_data});

    $.ajax({
            "url": "/tasks"
            ,"type": "POST"
            ,"dataType": "json"
            ,"contentType": "application/json"
            ,"data": data
    }).done(function (data, textStatus, jqXHR) {

		console.log('TASK_ID = '+data);
        $("#task_id").val(data);
        start_task_mapping(data);

    }).fail(handleRequestError);
}

function start_task_mapping(task_id)
{
    console.log('start_task_mapping->');
	/***
    set_task_status(task_id, REQ_MAPPING).done(function (data, textStatus, jqXHR){

        TAMER_ID = setInterval(function(){check_task_mapping_status(task_id)}, TIMER_INTERVAL);

    }).fail(function(jqXHR, textStatus, errorThrown){
		console.log('start_task_mapping->set_task_status->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
	***/
	TAMER_ID = setInterval(function(){check_task_mapping_status(task_id)}, TIMER_INTERVAL);

}

function check_task_mapping_status(task_id)
{
    console.log('check_task_mapping_status->');
	
    get_task_status(task_id).done(function (data, textStatus, jqXHR){

        console.log('status='+data)
		if (data==MAPPING_DONE)
		{
			clearInterval(TAMER_ID);
			load_task_reactions(task_id);
		} 

    }).fail(function(jqXHR, textStatus, errorThrown){
        clearInterval(TAMER_ID);
        console.log('ERROR:check_task_mapping_status->get_task_status->' + textStatus+ ' ' + errorThrown);
        handleRequestError();
    });

}


function load_task_reactions(task_id)
{
    console.log('load_task_reactions->');
	if (!task_id)
		task_id = get_task();
		
	if (isNaN(task_id))
	{
		alert('Session task not defined');
		return false;	
	}
	
    get_reactions_by_task(task_id).done(function (data, textStatus, jqXHR){

        Progress.done();

        try {
            display_task_reactions(data);
        }
        catch (err){console.log(err)}

    }).fail(function(jqXHR, textStatus, errorThrown){
        console.log('load_task_reactions->' + textStatus+ ' ' + errorThrown)});
        handleRequestError();
    return true;
}

function display_task_reactions(reactions)
{
    console.log('display_task_reactions->');
	
	// если скрыт редактор - покажем его
	show_editor();
	
    var jTbl = $("#reactions-tbd");
    jTbl.empty();
    var str = '';
    var reaction_ids = '';
    for (var i=0;i<reactions.length;i++)
    {
        var _reaction = reactions[i];
        var _r_id = _reaction.reaction_id;
        try {
            _temperature = _reaction.temperature;
            if (isEmpty(_temperature))
                _temperature = '';
        }catch(err){_temperature='';}

        try {
            _solvent_id = _reaction.solvents[0].id;
        }catch(err){_solvent_id='';}

        _s='';

        str+='<tr>';
        str+='<td class="reaction_id" reaction_id="'+_r_id+'"><a href="#">'+(i+1)+'</a></td>';
        str+='<td>';
        str+='<select  multiple="multiple" class="model" name="model_'+_r_id+'">';
        str+='<option value=""></option>';
        try {
            for (var j=0; j < _reaction.models.length; j++)
            {
                _m = _reaction.models[j];
                str+='<option value="'+_m.id+'">'+_m.name+'</option>';
            }
        }
        catch(err){console.log(err)}
        str+='</select>';
        str+='</td>';

        str+='<td><select    class="solvent" name="solvent_'+_r_id+'" solvent="'+_solvent_id+'" ></select></td>';
        str+='<td><input  class="temperature" name="temperature_'+_r_id+'" type="text" value="'+_temperature+'" /></td>';
        str+='</tr>';

        if (reaction_ids=='')
            reaction_ids+=_r_id;
        else
            reaction_ids+=','+_r_id;
    }
    jTbl.append(str);

    $('#task_reaction_ids').val(reaction_ids);

    jTbl.find(".reaction_id").click(function (){
                                        var r_id = $(this).attr('reaction_id');
                                        load_reaction(r_id);
                                    });

    /*********** Loading models ***************/
    try {
        get_models('').done(function(data, textStatus, jqXHR){

            var str = '';
            for (var i=0; i<data.length; i++)
            {
                var _id = data[i].id;
                var _name = data[i].name;
                str+='<option value="'+_id+'">'+_name+'</option>';
            }

            jTbl.find('.model').each(function(){
                var jSelect = $(this);
                // если модели еще не были загружены
                if (jSelect.find('option').length==1)
                    jSelect.append(str);
                //jSelect.find('option[value='+jSelect.attr('model')+']').attr('selected','selected');
            })
         })
    }
    catch (err){console.log('display_task_reactions->load models->'+err)}

    /*********** Loading solvents ***************/
    try {

        get_solvents().done(function(data, textStatus, jqXHR){

            var str = '<option value=""></option>';
            for (var i=0; i<data.length; i++)
            {
                var _id = data[i].id;
                var _name = data[i].name;
                str+='<option value="'+_id+'">'+_name+'</option>';
            }

            jTbl.find('.solvent').each(function(){
                var jSelect = $(this);
                jSelect.append(str);
                jSelect.find('option[value='+jSelect.attr('solvent')+']').attr('selected','selected');
            })
         })
    }
    catch (err){console.log('display_task_reactions->load models->'+err)}


    $("#reactions-div").show("normal");

    /*********** Add reaction save button to the editor ***************/
    var jso =  {
      "name": "saveButton", // JS String
      "image-url": "/static/images/save.png", // JS String
      "toolbar": "S" // JS String: "W" as West, "E" as East, "N" as North, "S" as South toolbar
     }

	// проверим - не были ли уже добавлена кнопка
	if (!isSaveMrvBtnExists)
	{
	    marvinSketcherInstance.addButton(jso, save_draw_reaction );
		isSaveMrvBtnExists=true;
	}

}

function load_reaction(reaction_id)
{
    console.log('load_reaction->');
    if (isNaN(reaction_id))
    {
        alert('An error occurred when loading the reaction');
        console.log('load_reaction-> reaction_id isNaN:'+reaction_id);
        return false;
    }
	Progress.start();

    get_reaction_structure(reaction_id).done(function (data, textStatus, jqXHR){

        Progress.done();
        $('#reaction_id').val(reaction_id);

        try {
            draw_moldata(data);
        }
        catch (err){console.log(err)}

    }).fail(function(jqXHR, textStatus, errorThrown){console.log('ERROR:show_reaction->' + textStatus+ ' ' + errorThrown)});
    return true;

}

function draw_moldata (data)
{
    try {
        marvinSketcherInstance.importStructure(MOL_FORMAT, data);
    }
    catch(err){
        console.log('draw_moldata->'+err)
    }
}

function save_draw_reaction ()
{
	marvinSketcherInstance.exportStructure(MOL_FORMAT).then(function(source) {

		console.log(source);
		if (isMolEmpty(source))
		{
			alert('You need enter a reaction');
			return false;
		}
		else
			upload_draw_reaction(source);

	}, function(error) {
		alert("Molecule export failed:"+error);
	});

}

function upload_draw_reaction(data)
{
    console.log('upload_draw_reaction->');
	
	var reaction_id = $('#reaction_id').val();
	if (reaction_id!='')
	{
	    Progress.start();
	    put_reaction_structure(reaction_id,data ).done(function (data, textStatus, jqXHR) {

        Progress.done();
        alert('Reaction has been saved successfully');

    	}).fail(handleRequestError);
	}
	else
	{
        alert('Please, select a reaction from table');
	}
}

function upload_reaction_form()
{
    Progress.start();
    console.log('upload_reaction_form->');
    var task_id = $("#task_id").val();
    if (isEmpty(task_id))
    {
        alert('Session task not defined');
		Progress.done();
        return false;
    }
    var data = {};
	 $("#reactions-form").serializeArray().map(function(x){
		if (data[x.name])
			data[x.name] = data[x.name] +','+ x.value;
		else
			data[x.name] = x.value;
	});
	console.log(data);
	
    return $.post("/task_modelling/"+task_id, data).done(function (data, textStatus, jqXHR){

        console.log('form upload '+data);
        start_modelling();

    }).fail(function(jqXHR, textStatus, errorThrown){
        alert('Upload  reactions failure');
		console.log('upload_reaction_forms->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
}

function start_modelling()
{
    console.log('start_modelling->');

    var task_id = $("#task_id").val();
    set_task_status(task_id, REQ_MODELLING).done(function (data, textStatus, jqXHR){

        TAMER_ID = setInterval(function(){check_modelling_status(task_id)}, TIMER_INTERVAL);

    }).fail(function(jqXHR, textStatus, errorThrown){
		console.log('start_modelling->set_task_status->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});
}


function check_modelling_status(task_id)
{
    console.log('check_modelling_status->'+task_id);

    get_task_status(task_id).done(function (data, textStatus, jqXHR){

    	if (data==MODELLING_DONE)
		{
			clearInterval(TAMER_ID);
			load_modelling_results(task_id);
		}

    }).fail(function(jqXHR, textStatus, errorThrown){
        clearInterval(TAMER_ID);
        console.log('ERROR:check_modelling_status->get_task_status->' + textStatus+ ' ' + errorThrown);
        handleRequestError();
    });

}

function load_modelling_results(task_id)
{
    console.log('load_modelling_results->');
	if (!task_id)
		task_id = get_task();
		
	if (isNaN(task_id))
	{
		alert('Session task not defined');
		return false;	
	}	
	
    $.get("/task_modelling/"+task_id).done(function (data, textStatus, jqXHR){

        Progress.done();
        try {
            display_modelling_results(data);
        }
        catch (err){console.log('load_modelling_results->'+err)}

    }).fail(function(jqXHR, textStatus, errorThrown){console.log('ERROR:load_modelling_results->' + textStatus+ ' ' + errorThrown)});
    return true;
}


function load_reaction_img(reaction_id)
{
    return $.get("/reaction_img/"+reaction_id);

}
function display_modelling_results(results)
{
	// скроем редактор
	hide_editor();
	// скроем таблицу с реакциями
	hide_reactions();
		
    var jTbl = $("#results-tbody");
    jTbl.empty();
    var str = '';
    for (var i=0;i<results.length; i++)
    {
        var result = results[i];
        r_id = result.reaction_id;
        var reaction_results = result.results;
        str+='<tr>';
        str+='<td rowspan="'+reaction_results.length+'"><img class="reaction_img" reaction_id="'+r_id+'" src=""  alt="bla-bla"/></td>';

        for (var j=0;j<reaction_results.length;j++)
        {
            _res = reaction_results[j];
            str+='<td>'+_res.model+'</td>';
            str+='<td>'+_res.param+'</td>';
            str+='<td>'+_res.value+'</td>';
            str+='</tr>';
        }
    }

    jTbl.append(str);
    $("#results-div").show("normal");
    jTbl.find('.reaction_img').each(function(){

        var jImg = $(this);
		/*
        load_reaction_img( jImg.attr('reaction_id' )).done(function (data, textStatus, jqXHR){

            try {
                var response = JSON.parse(data)
                var img_url = response['contentUrl'];
                jImg.attr('src',img_url);
            }
            catch(err){console.log(err)}

        })
		*/
		get_reaction_structure( jImg.attr('reaction_id') ).done(function(data, textStatus, jqXHR){
			
			var settings = {
					'carbonLabelVisible' : false,
					'cpkColoring' : true,
					'implicitHydrogen' : false,
					'width' : 300,
					'height' : 100
			};		
			try {	
				var dataUrl = marvin.ImageExporter.mrvToDataUrl(data,"image/png",settings);
				jImg.attr('src',dataUrl);						
			}
			catch(err){
				console.log(err);
			}
		});


    });

}

/*
				var settings = {
						'carbonLabelVisible' : $("#chbx-carbonVis").is(':checked'),
						'cpkColoring' : $("#chbx-coloring").is(':checked'),
						'implicitHydrogen' : $("#implicittype").val(),
						'width' : parseInt($("#w").val(), 10),
						'height' : parseInt($("#h").val(), 10)
				};
				var dataUrl = marvin.ImageExporter.molToDataUrl($("#text").val(),"image/png",settings);
				$("#image").attr("src", dataUrl);
*/

//curl http://127.0.0.1:5000/tasks   -d "reaction_structure=<xml></xml>" -X POST
//curl http://127.0.0.1:5000/task/ce99375015b1ee7ac4d87bfee941296b   -d "task_status=0" -X GET
//curl http://127.0.0.1:5000/reaction/2   -d "model=1,2" -X PUT
