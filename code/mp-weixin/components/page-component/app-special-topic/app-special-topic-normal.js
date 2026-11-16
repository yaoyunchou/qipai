(global["webpackJsonp"]=global["webpackJsonp"]||[]).push([["components/page-component/app-special-topic/app-special-topic-normal"],{"069b":function(t,n,e){"use strict";Object.defineProperty(n,"__esModule",{value:!0}),n.default=void 0;var i={name:"app-special-topic",props:{topic_list:{type:Array,default:function(){return[]}},count:{type:Number,default:function(){return 2}},icon:String,logo_1:String,logo_2:String},computed:{newDataList:function(){if(2===this.count){for(var t=[],n=0;n<Math.ceil(this.topic_list.length/this.count);n++)t.push(this.topic_list.slice(n*this.count,(n+1)*this.count));return t}}}};n.default=i},"26a4":function(t,n,e){"use strict";e.r(n);var i=e("8280"),c=e("a70e");for(var u in c)["default"].indexOf(u)<0&&function(t){e.d(n,t,(function(){return c[t]}))}(u);e("5853");var o,a=e("f0c5"),r=Object(a["a"])(c["default"],i["b"],i["c"],!1,null,"2b4328d4",null,!1,i["a"],o);n["default"]=r.exports},5853:function(t,n,e){"use strict";var i=e("c15a"),c=e.n(i);c.a},8280:function(t,n,e){"use strict";var i;e.d(n,"b",(function(){return c})),e.d(n,"c",(function(){return u})),e.d(n,"a",(function(){return i}));var c=function(){var t=this,n=t.$createElement;t._self._c},u=[]},a70e:function(t,n,e){"use strict";e.r(n);var i=e("069b"),c=e.n(i);for(var u in i)["default"].indexOf(u)<0&&function(t){e.d(n,t,(function(){return i[t]}))}(u);n["default"]=c.a},c15a:function(t,n,e){}}]);
;(global["webpackJsonp"] = global["webpackJsonp"] || []).push([
    'components/page-component/app-special-topic/app-special-topic-normal-create-component',
    {
        'components/page-component/app-special-topic/app-special-topic-normal-create-component':(function(module, exports, __webpack_require__){
            __webpack_require__('543d')['createComponent'](__webpack_require__("26a4"))
        })
    },
    [['components/page-component/app-special-topic/app-special-topic-normal-create-component']]
]);
