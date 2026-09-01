// SPDX-FileCopyrightText: 2026 Mark G. Russell
// SPDX-License-Identifier: MIT
#include "map_view.hpp"
#include "map_renderer_frontend.hpp"
#include "glfw_backend.hpp"
#include <mbgl/gfx/backend.hpp>
#include <mbgl/gfx/backend_scope.hpp>
#include <mbgl/renderer/renderer.hpp>
#include <mbgl/renderer/query_options.hpp>
#include <mbgl/util/logging.hpp>
#define GLFW_INCLUDE_ES3
#define GLFW_EXPOSE_NATIVE_X11
#define GL_GLEXT_PROTOTYPES
#include <GLFW/glfw3.h>
#if defined(__linux__)
#include <GLFW/glfw3native.h>
#include <X11/Xlib.h>
#endif
#include <cmath>
#include <cstdlib>
#include <iostream>
#include <string>

namespace {
void glfwError(int error,const char* description){mbgl::Log::Error(mbgl::Event::OpenGL,std::string("GLFW error (")+std::to_string(error)+"): "+description);}
std::string stringProperty(const mbgl::Feature& feature,const char* key){const auto it=feature.properties.find(key);if(it==feature.properties.end()||!it->second.is<std::string>())return {};return it->second.get<std::string>();}
#if defined(__linux__)
void embedInX11Parent(GLFWwindow* window){const char* value=std::getenv("OPENROADCODE_MAP_PARENT_WINDOW");if(!value||!*value)return;char* end=nullptr;const unsigned long parentId=std::strtoul(value,&end,0);if(end==value||*end!='\0'||parentId==0){std::cerr<<"[map_renderer] invalid OPENROADCODE_MAP_PARENT_WINDOW="<<value<<'\n';return;}Display* display=glfwGetX11Display();const Window child=glfwGetX11Window(window);if(!display||child==0){std::cerr<<"[map_renderer] GLFW X11 native window is unavailable\n";return;}XWindowAttributes a{};if(!XGetWindowAttributes(display,static_cast<Window>(parentId),&a)){std::cerr<<"[map_renderer] X11 parent window unavailable\n";return;}XReparentWindow(display,child,static_cast<Window>(parentId),0,0);XResizeWindow(display,child,a.width,a.height);XMapWindow(display,child);XFlush(display);glfwSetWindowSize(window,a.width,a.height);}
#endif
}
MapView::MapView(const mbgl::ResourceOptions&,const mbgl::ClientOptions&){glfwSetErrorCallback(glfwError);if(!glfwInit())std::exit(1);if(mbgl::gfx::Backend::GetType()==mbgl::gfx::Backend::Type::OpenGL){
#if MBGL_WITH_EGL
 glfwWindowHint(GLFW_CONTEXT_CREATION_API,GLFW_EGL_CONTEXT_API);
#endif
 glfwWindowHint(GLFW_CLIENT_API,GLFW_OPENGL_ES_API);glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR,3);glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR,0);glfwWindowHint(GLFW_RED_BITS,8);glfwWindowHint(GLFW_GREEN_BITS,8);glfwWindowHint(GLFW_BLUE_BITS,8);glfwWindowHint(GLFW_ALPHA_BITS,8);glfwWindowHint(GLFW_STENCIL_BITS,8);glfwWindowHint(GLFW_DEPTH_BITS,16);}else glfwWindowHint(GLFW_CLIENT_API,GLFW_NO_API);window=glfwCreateWindow(width,height,"OpenRoadCode Map Renderer",nullptr,nullptr);if(!window){glfwTerminate();std::exit(1);}
#if defined(__linux__)
 embedInX11Parent(window);
#endif
 glfwSetWindowUserPointer(window,this);glfwSetWindowSizeCallback(window,onWindowResize);glfwSetFramebufferSizeCallback(window,onFramebufferResize);glfwSetCursorPosCallback(window,onMouseMove);glfwSetMouseButtonCallback(window,onMouseClick);glfwSetScrollCallback(window,onScroll);backend=GLFWBackend::Create(window,true);glfwGetWindowSize(window,&width,&height);pixelRatio=static_cast<float>(backend->getSize().width)/static_cast<float>(width);glfwMakeContextCurrent(nullptr);}
MapView::~MapView(){if(window){glfwDestroyWindow(window);window=nullptr;}glfwTerminate();}
float MapView::getPixelRatio()const{return pixelRatio;} mbgl::Size MapView::getSize()const{return{static_cast<uint32_t>(width),static_cast<uint32_t>(height)};} mbgl::gfx::RendererBackend& MapView::getRendererBackend(){return backend->getRendererBackend();} void MapView::setMap(mbgl::Map* value){map=value;} void MapView::setRendererFrontend(MapRendererFrontend* value){rendererFrontend=value;} void MapView::setShouldClose(){glfwSetWindowShouldClose(window,GLFW_TRUE);glfwPostEmptyEvent();}
void MapView::onWindowResize(GLFWwindow* window,int w,int h){auto* v=static_cast<MapView*>(glfwGetWindowUserPointer(window));if(!v)return;v->width=w;v->height=h;if(v->map)v->map->setSize({static_cast<uint32_t>(w),static_cast<uint32_t>(h)});}
void MapView::onFramebufferResize(GLFWwindow* window,int w,int h){auto* v=static_cast<MapView*>(glfwGetWindowUserPointer(window));if(!v)return;v->backend->setSize({static_cast<uint32_t>(w),static_cast<uint32_t>(h)});v->invalidate();}
void MapView::onScroll(GLFWwindow* window,double,double y){auto* v=static_cast<MapView*>(glfwGetWindowUserPointer(window));if(!v||!v->map)return;const double delta=y*40.0;double scale=2.0/(1.0+std::exp(-std::abs(delta)/100.0));if(delta<0)scale=1.0/scale;v->map->scaleBy(scale,{v->lastX,v->lastY});}
void MapView::onMouseClick(GLFWwindow* window,int button,int action,int modifiers){auto* v=static_cast<MapView*>(glfwGetWindowUserPointer(window));if(!v||!v->map||button!=GLFW_MOUSE_BUTTON_LEFT)return;if(action==GLFW_PRESS){v->pressX=v->lastX;v->pressY=v->lastY;}v->tracking=action==GLFW_PRESS;v->map->setGestureInProgress(v->tracking);if(action==GLFW_RELEASE){const double moved=std::hypot(v->lastX-v->pressX,v->lastY-v->pressY);const double now=glfwGetTime();if(now-v->lastClick<0.4){v->map->scaleBy(modifiers&GLFW_MOD_SHIFT?0.5:2.0,{v->lastX,v->lastY},mbgl::AnimationOptions{{mbgl::Milliseconds(500)}});}else if(moved<8.0)v->selectPoiAt(v->lastX,v->lastY);v->lastClick=now;}}
void MapView::selectPoiAt(double x,double y){if(!map||!rendererFrontend||!rendererFrontend->getRenderer()||!poiSelectedCallback)return;const mbgl::ScreenCoordinate point{x,y};const mbgl::RenderedQueryOptions options{{{"poi-labels-food","poi-labels-important","fuel-focus-label","grocery-focus-label"}}, {}};const auto features=rendererFrontend->getRenderer()->queryRenderedFeatures(point,options);if(features.empty())return;const auto& f=features.front();std::string name=stringProperty(f,"name:latin");if(name.empty())name=stringProperty(f,"name");if(name.empty())return;const auto coordinate=map->latLngForPixel(point);const auto brand=stringProperty(f,"brand");const auto sourceClass=stringProperty(f,"class");const auto sourceSubclass=stringProperty(f,"subclass");std::cout<<"[map_renderer] selected POI: "<<name<<'\n';poiSelectedCallback(name,brand,sourceClass,sourceSubclass,coordinate.latitude(),coordinate.longitude());}
void MapView::onMouseMove(GLFWwindow* window,double x,double y){auto* v=static_cast<MapView*>(glfwGetWindowUserPointer(window));if(!v||!v->map)return;if(v->tracking){const double dx=x-v->lastX,dy=y-v->lastY;if(dx!=0||dy!=0)v->map->moveBy({dx,dy});}v->lastX=x;v->lastY=y;}
void MapView::render(){if(!dirty||!rendererFrontend)return;dirty=false;mbgl::gfx::BackendScope scope{backend->getRendererBackend()};rendererFrontend->render();}
void MapView::run(){auto callback=[&](){if(glfwWindowShouldClose(window)){runLoop.stop();return;}glfwPollEvents();if(updateCallback)updateCallback();render();
#ifndef __APPLE__
 runLoop.updateTime();
#endif
 };frameTick.start(mbgl::Duration::zero(),mbgl::Milliseconds(1000/60),callback);
#if defined(__APPLE__)
 while(!glfwWindowShouldClose(window))runLoop.run();
#else
 runLoop.run();
#endif
}
void MapView::invalidate(){dirty=true;glfwPostEmptyEvent();} void MapView::onWillStartRenderingFrame(){invalidate();} void MapView::setUpdateCallback(std::function<void()> callback){updateCallback=std::move(callback);} void MapView::setPoiSelectedCallback(PoiSelectedCallback callback){poiSelectedCallback=std::move(callback);}
