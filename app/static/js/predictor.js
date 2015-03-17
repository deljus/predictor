var marvinSketcherInstance;

$(document).ready(function handleDocumentReady (e) {
	var p = MarvinJSUtil.getEditor("#sketch");
	p.then(function (sketcherInstance) {
		marvinSketcherInstance = sketcherInstance;
		initControl();
	}, function (error) {
		alert("Cannot retrieve sketcher instance from iframe:"+error);
	});
});

function handleRequestError()
{
    NProgress.done();
}


$(function() {
    $('#upload-file-btn').click(function() {

        if ($('#file').val()=='')
        {
            alert('You have to select file');
            return false;
        }
        var form_data = new FormData($('#upload-file')[0]);
        $.ajax({
            type: 'POST',
            url: '/uploadajax',
            data: form_data,
            contentType: false,
            cache: false,
            processData: false,
            async: false,
            success: function(data) {
                alert('File has been uploaded successfully! ');
            },
        });
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
    console.log('get_task_status->'+status);
    return $.ajax({
        "url": "/task_status/"+task_id
        ,"type": "GET"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": ""
    });
}

function get_reaction_structure(reaction_id)
{
    console.log('get_reaction_structure->'+reaction_id);
    return $.ajax({
        "url": "/reaction_structure/"+reaction_id
        ,"type": "GET"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": ""
    });
}

function put_reaction_structure(reaction_id, data)
{ 
    console.log('put_reaction_structure->');
    var data = JSON.stringify({"reaction_structure": data});

    return $.ajax({
            "url": "/reaction_structure/"+reaction_id
            ,"type": "PUT"
            ,"dataType": "json"
            ,"contentType": "application/json"
            ,"data": data
    }); 	
}

function get_models()
{
    console.log('get_models->');
    return $.ajax({
        "url": "/models"
        ,"type": "GET"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": ""
    });
}

function get_solvents()
{
    console.log('get_solvents->');
    return $.ajax({
        "url": "/solvents"
        ,"type": "GET"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": ""
    });
}

function get_reactions_by_task(task_id)
{
    return $.ajax({
        "url": "/task_reactions/"+task_id
        ,"type": "GET"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": {}
    })
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

// progress bar
$(function() {
  NProgress.configure({ parent: '#div-editor' });
});
/******************************************************/

function initControl ()
{
	// get mol button
	$("#btn-upload-data").on("click", function (e) {
        upload_data();
	});
}

function upload_data()
{
    console.log('upload_data->');

    var file = false;
    if (file)
    {
        upload_task_file_data();
    }
    else
    {
		marvinSketcherInstance.exportStructure(MOL_FORMAT).then(function(source) {

			console.log(source);

            if (isMolEmpty(source))
            {
                alert('You need enter a reaction');
                return false;
            }
            else
                upload_task_draw_data(source);

		}, function(error) {
			alert("Molecule export failed:"+error);
		});
    }
}

function upload_task_file_data()
{
    NProgress.start();
	console.log('upload_task_file_data->');
}

function upload_task_draw_data(draw_data)
{
    NProgress.start();
    console.log('upload_task_draw_data->');
    var data = JSON.stringify({"reaction_structure": draw_data});

    $.ajax({
            "url": "/tasks"
            ,"type": "POST"
            ,"dataType": "json"
            ,"contentType": "application/json"
            ,"data": data
    }).done(function (data, textStatus, jqXHR) {

        $("#task_id").val(data);
        start_task_mapping(data);

    }).fail(handleRequestError);
}

function start_task_mapping(task_id)
{
    console.log('start_task_mapping->');
	
    set_task_status(task_id, REQ_MAPPING).done(function (data, textStatus, jqXHR){

        TAMER_ID = setInterval(function(){check_task_mapping_status(task_id)}, TIMER_INTERVAL);

    }).fail(function(jqXHR, textStatus, errorThrown){
		console.log('start_task_mapping->set_task_status->' + textStatus+ ' ' + errorThrown);
		handleRequestError();
	});

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
	
    get_reactions_by_task(task_id).done(function (data, textStatus, jqXHR){

        NProgress.done();

        console.log(data);
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
	
    var jTbl = $("#reactions-tbody");
    jTbl.empty();
    var str = '';
    var reaction_ids = '';
    for (var i=0;i<reactions.length;i++)
    {
        var _r = reactions[i];
        var _r_id = _r.reaction_id;
        try {
            _t = _r.temperature;

            if (isEmpty(_t))
                _t = '';
        }catch(err){_t='';}
        try {_m = _r.model}catch(err){_m='';}
        try {_s = _r.solvent}catch(err){_s='';}

        str+='<tr>';
        str+='<td class="reaction_id" reaction_id="'+_r_id+'">'+(i+1)+'</td>';
        str+='<td><select class="model" name="model_'+_r_id+'" model="'+_m+'" ></select></td>';
        str+='<td><select class="solvent" name="solvent_'+_r_id+'" solvent="'+_s+'" ></select></td>';
        str+='<td><input  class="temperature" name="temperature_'+_r_id+'" type="text" value="'+_t+'" /></td>';
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

        get_models().done(function(data, textStatus, jqXHR){

            var str = '<option value=""></option>';
            for (var i=0; i<data.length; i++)
            {
                var _id = data[i].id;
                var _name = data[i].name;
                str+='<option value="'+_id+'">'+_name+'</option>';
            }

            jTbl.find('.model').each(function(){
                var jSelect = $(this);
                jSelect.append(str);
                jSelect.find('option[value='+jSelect.attr('model')+']').attr('selected','selected');

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


    $("#reactions-pnl").show("normal");

    /*********** Add reaction save button to the editor ***************/
    var jso =  {
      "name": "saveButton", // JS String
      "image-url": "/static/images/save.png", // JS String
      "toolbar": "S" // JS String: "W" as West, "E" as East, "N" as North, "S" as South toolbar
     }

    marvinSketcherInstance.addButton(jso, save_draw_reaction );

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
	NProgress.start();

    get_reaction_structure(reaction_id).done(function (data, textStatus, jqXHR){

        NProgress.done();
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
	    NProgress.start();
	    put_reaction_structure(reaction_id,data ).done(function (data, textStatus, jqXHR) {

        NProgress.done();
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
    NProgress.start();
    console.log('upload_reaction_form->');
    var task_id = $("#task_id").val();
    var data = {};
    $("#reactions-form").serializeArray().map(function(x){data[x.name] = x.value;});
    data = JSON.stringify(data);
    return $.ajax({
        "url": "/task_modelling/"+task_id
        ,"type": "PUT"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": data
    }).done(function (data, textStatus, jqXHR){

        console.log('form upload '+data);
        start_modelling();

    }).fail(function(jqXHR, textStatus, errorThrown){
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
    console.log('check_modelling_status->');

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
    $.ajax({
        "url": "/task_modelling/"+task_id
        ,"type": "GET"
        ,"dataType": "json"
        ,"contentType": "application/json"
        ,"data": ""
    }).done(function (data, textStatus, jqXHR){

        NProgress.done();
        console.log(data);
        try {
            display_modelling_results(data);
        }
        catch (err){console.log('load_modelling_results->'+err)}

    }).fail(function(jqXHR, textStatus, errorThrown){console.log('ERROR:load_modelling_results->' + textStatus+ ' ' + errorThrown)});
    return true;
}



function display_modelling_results(results)
{
    var jTbl = $("#results-tbody");
    jTbl.empty();
    var str = '';
    for (var i=0;i<results.length; i++)
    {
        var result = results[i];
        r_id = result.reaction_id;
        var reaction_results = result.results;
        str+='<tr>';
        str+='<td rowspan="'+reaction_results.length+'">'+(i+1)+'</td>';

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
    $("#results-pnl").show("normal");
}

//curl http://127.0.0.1:5000/tasks   -d "reaction_structure=<xml></xml>" -X POST
//curl http://127.0.0.1:5000/task/ce99375015b1ee7ac4d87bfee941296b   -d "task_status=0" -X GET
//curl http://127.0.0.1:5000/task_reactions/584534ef05de9a8ec3061e4a5a46d8ce   -d "task_status=1" -X GET
