$(function(){
    // カウントダウン処理----------------------------------------------------------------------------------------
    var todoInfo = document.getElementById('todo-info').textContent;
    todoInfo = JSON.parse(todoInfo);
    const goalTime = todoInfo.expectedTime;
    const halfTime  = Math.floor(goalTime / 2);
    const alertTime = Math.floor(goalTime / 4);
    var timeLeftTag = $("#time-left");
    var timer;
    var timeLeft = goalTime - todoInfo.actualTime;
    // var counter = todoInfo.actual_time;
    var isCounting = false;

    const safeColor = 'Blue';
    const halfColor = 'Green';
    const alertColor = 'Orange';
    const deadColor = 'Red';
    var isDefaultColor = true;
    var defaultColor = safeColor;

    function countDown() {
        const timeList = [0, alertTime, halfTime, goalTime];
        const colorList = [deadColor, alertColor, halfColor, safeColor];
        // var left = goalTime - counter;
        timeLeft--;

        // 制限時間を終了したら超過時間を表示する。
        if (timeLeft < 0) {
            $('#help-text').text('超過時間');
            let text = secToHMS(-timeLeft);
            timeLeftTag.text(text);
            // counter++;
            return 
        }
        var text = secToHMS(timeLeft);
        for (let i = 0; i < 4; i++) {
            if (timeLeft === timeList[i]) {
                defaultColor = colorList[i];
                timeLeftTag.css('color', defaultColor);
                isDefaultColor = true;
            }
        }
        timeLeftTag.text(text);
    }
    // time(sec)をhh:mm:ssの形式に変換する。
    function secToHMS(time) {
        var hour = Math.floor(time / (60 * 60));
        var min = Math.floor((time % (60 * 60)) / 60);
        var sec = Math.floor(time % (60 * 60)) % 60;

        var hourNum = ('0' + hour).slice(-2);
        var minNum = ('0' + min).slice(-2);
        var secNum = ('0' + sec).slice(-2);
        return hourNum + ':' + minNum + ':' + secNum;
    }

    function startTimer(){
        isCounting = true;
        timer = setInterval(countDown, 1000);
    }
    function pauseTimer(){
        isCounting = false;
        clearInterval(timer);
    }

    timeLeftTag.click(function(){
        if (timeLeft <= 0) {
            return false;
        }
        var changeColor;
        if (isDefaultColor) {
            isDefaultColor = false;
            changeColor = safeColor;
        } else {
            isDefaultColor = true;
            changeColor = defaultColor;
        }
        timeLeftTag.css('color', changeColor);
    });

    // ダイアログ表示---------------------------------------------------------------------------------------------------
    $('#start-dialog').dialog({
        modal: true, 
        title: '確認', 
        buttons: {
            '開始': function(){
                startTimer();
                $(this).dialog("close");
            }
        }, 
        open: function(){$(".ui-dialog-titlebar-close", $(this).closest(".ui-dialog")).hide();}
    });
    $('#back-dialog').dialog({
        modal: true, 
        autoOpen: false, 
        title: '確認', 
        buttons: {
            '前のToDoに戻る': function(){
                $('#back-form input[name="actual_time"]').val(goalTime - timeLeft); 
                $('#back-form').submit();
            }, 
            'キャンセル': function(){
                startTimer();
                $('#back-dialog').dialog('close');
            }
        }
    });
    $("#drop-dialog").dialog({
        modal: true, 
        autoOpen: false, 
        title: '警告', 
        buttons: {
            '中断': function(){
                // 中断処理
                $('#drop-form').attr('target', 'parent-window');
                $('#drop-form input[name="actual_time"]').val(goalTime - timeLeft);
                $('#drop-form').submit();
                $(this).dialog("close");
                window.close();
            }, 
            'キャンセル': function(){
                startTimer();
                $(this).dialog("close");
            }
        }
    });

    // ボタン押下時の処理----------------------------------------------------------------------------------------------
    if (todoInfo.order === 1) {
        $('#back-form button').css({
            'background-color' : '#ecedee', 
            'color'            : '#a2a6ac', 
            'border-color'     : '#ecedee'
        });
        $('#back-form button:hover').css({
            'background-color' : '#ecedee', 
            'color'            : '#a2a6ac', 
            'border-color'     : '#ecedee'
        });
    }
    $('#back-form button').click(function(){
        console.log(todoInfo.order)
        if (todoInfo.order === 1) {
            return false;
        }
        pauseTimer();
        $('#back-dialog').dialog('open');
    });
    $('#pause-restart-btn').click(function(){
        if (isCounting) {
            $('#pause-restart-btn').text('Restart');
            pauseTimer();
        } else {
            $('#pause-restart-btn').text('Pause');
            startTimer();
        }
    });
    $('#next-form button').click(function(){
        $('#next-form input[name="actual_time"]').val(goalTime - timeLeft);

        if (todoInfo.order === todoInfo.todoNumInWorkdate) {
            $('#next-form').attr('target', 'parent-window');
            $('#next-form').submit();
            window.close();
        } else {
            $('#next-form').submit();
        }
    });
    $("#drop-form button").click(function(){
        pauseTimer();
        $('#drop-dialog').dialog('open');
    });
});